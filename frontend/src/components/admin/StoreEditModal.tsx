import { useEffect, useState } from "react";
import { adminApi, StoreRow, StoreUpdate } from "../../api/admin";
import "../../pages/admin/admin-theme.css";

interface Props {
  store: StoreRow | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function StoreEditModal({ store, onClose, onSaved }: Props) {
  const [form, setForm] = useState<StoreUpdate>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (store) {
      setForm({
        name: store.name,
        location: store.location,
        phone: store.phone ?? "",
        business_type: store.business_type ?? "",
        lat: store.lat,
        lon: store.lon,
        is_active: store.is_active,
      });
    }
  }, [store]);

  if (!store) return null;

  const save = async () => {
    setSaving(true);
    try {
      await adminApi.updateStore(store.id, {
        ...form,
        phone: form.phone || null,
        business_type: form.business_type || null,
      });
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <h3>Edit store</h3>
        <div className="admin-form-grid">
          <label>
            Store name
            <input
              className="admin-input"
              value={form.name ?? ""}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            Location
            <input
              className="admin-input"
              value={form.location ?? ""}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
            />
          </label>
          <div className="admin-form-row">
            <label>
              Phone
              <input
                className="admin-input"
                value={form.phone ?? ""}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </label>
            <label>
              Business type
              <input
                className="admin-input"
                value={form.business_type ?? ""}
                onChange={(e) => setForm({ ...form, business_type: e.target.value })}
              />
            </label>
          </div>
          <div className="admin-form-row">
            <label>
              Latitude
              <input
                className="admin-input"
                type="number"
                step="any"
                value={form.lat ?? ""}
                onChange={(e) => setForm({ ...form, lat: parseFloat(e.target.value) })}
              />
            </label>
            <label>
              Longitude
              <input
                className="admin-input"
                type="number"
                step="any"
                value={form.lon ?? ""}
                onChange={(e) => setForm({ ...form, lon: parseFloat(e.target.value) })}
              />
            </label>
          </div>
          <div className="admin-toggle-row">
            <span style={{ fontSize: "0.85rem" }}>Store active</span>
            <input
              type="checkbox"
              checked={form.is_active ?? true}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
          </div>
        </div>
        <div className="admin-modal-actions">
          <button type="button" className="admin-btn admin-btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="admin-btn admin-btn-primary" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
