from datetime import date, timedelta

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.store import Forecast, Product, Transaction


def _fallback_forecasts(product: Product, df: pd.DataFrame, days: int) -> list[Forecast]:
    avg = df["y"].mean() if not df.empty else 5.0
    forecasts = []
    for i in range(days):
        fd = date.today() + timedelta(days=i + 1)
        pred = avg * (1.1 if fd.weekday() >= 5 else 1.0)
        forecasts.append(
            Forecast(
                product_id=product.id,
                forecast_date=fd,
                predicted_qty=round(pred, 2),
                lower_bound=round(pred * 0.7, 2),
                upper_bound=round(pred * 1.3, 2),
                confidence=0.65,
            )
        )
    return forecasts


def _build_daily_series(session: Session, product_id: int) -> pd.DataFrame:
    rows = session.execute(
        select(
            func.date(Transaction.sold_at).label("ds"),
            func.sum(Transaction.quantity).label("y"),
        )
        .where(Transaction.product_id == product_id)
        .group_by(func.date(Transaction.sold_at))
        .order_by(func.date(Transaction.sold_at))
    ).all()

    if not rows:
        return pd.DataFrame(columns=["ds", "y"])

    df = pd.DataFrame([{"ds": pd.to_datetime(r.ds), "y": float(r.y)} for r in rows])
    df["weekend"] = (df["ds"].dt.dayofweek >= 5).astype(int)
    return df


def run_prophet_for_product(session: Session, product: Product, days: int = 7) -> list[Forecast]:
    df = _build_daily_series(session, product.id)
    if df.empty or len(df) < 7:
        return _fallback_forecasts(product, df, days)

    try:
        from prophet import Prophet

        model = Prophet(yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=False)
        model.add_regressor("weekend")
        model.fit(df)

        future = model.make_future_dataframe(periods=days)
        future["weekend"] = (future["ds"].dt.dayofweek >= 5).astype(int)
        prediction = model.predict(future).tail(days)

        forecasts = []
        for _, row in prediction.iterrows():
            forecasts.append(
                Forecast(
                    product_id=product.id,
                    forecast_date=row["ds"].date(),
                    predicted_qty=round(max(row["yhat"], 0), 2),
                    lower_bound=round(max(row["yhat_lower"], 0), 2),
                    upper_bound=round(max(row["yhat_upper"], 0), 2),
                    confidence=0.82,
                )
            )
        return forecasts
    except Exception:
        return _fallback_forecasts(product, df, days)


def run_all_forecasts(session: Session, top_n: int = 20) -> int:
    products = session.execute(
        select(Product)
        .join(Transaction, Transaction.product_id == Product.id)
        .group_by(Product.id)
        .order_by(func.sum(Transaction.quantity * Transaction.unit_price).desc())
        .limit(top_n)
    ).scalars().all()

    if not products:
        products = session.execute(select(Product).limit(top_n)).scalars().all()

    count = 0
    for product in products:
        session.execute(delete(Forecast).where(Forecast.product_id == product.id))
        forecasts = run_prophet_for_product(session, product)
        session.add_all(forecasts)
        count += len(forecasts)
    session.commit()
    return count
