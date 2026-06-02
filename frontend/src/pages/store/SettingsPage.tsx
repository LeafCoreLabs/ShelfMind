import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import AppShell from "../../components/layout/AppShell";
import { storeApi } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import "./store-theme.css";

export default function SettingsPage() {
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [phone, setPhone] = useState("");
  const [businessType, setBusinessType] = useState("");
  const [gstin, setGstin] = useState("");
  const [placeOfSupply, setPlaceOfSupply] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    storeApi.getSettings().then((s) => {
      setName(String(s.name ?? ""));
      setLocation(String(s.location ?? ""));
      setPhone(String(s.phone ?? ""));
      setBusinessType(String(s.business_type ?? ""));
      setGstin(String(s.gstin ?? ""));
      setPlaceOfSupply(String(s.place_of_supply ?? ""));
    });
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    await storeApi.updateSettings({
      name,
      location,
      phone,
      business_type: businessType,
      gstin,
      place_of_supply: placeOfSupply,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <AppShell {...STORE_SHELL} title="Shop Profile" subtitle="Your store details and business preferences">
      <StaggerGrid className="admin-grid-2">
        <StaggerItem>
          <AnimatedPanel style={{ maxWidth: 480 }}>
            <div className="admin-card-title">Store details</div>
            <form onSubmit={save} className="admin-form-grid">
              <label>
                Store name
                <input className="admin-input" value={name} onChange={(e) => setName(e.target.value)} />
              </label>
              <label>
                Location
                <input className="admin-input" value={location} onChange={(e) => setLocation(e.target.value)} />
              </label>
              <label>
                Phone
                <input className="admin-input" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </label>
              <label>
                Business type
                <input className="admin-input" value={businessType} onChange={(e) => setBusinessType(e.target.value)} />
              </label>
              <button type="submit" className="admin-btn admin-btn-primary">Save changes</button>
              {saved && <p className="admin-job-msg">Settings saved.</p>}
            </form>
          </AnimatedPanel>
        </StaggerItem>
        <StaggerItem>
          <AnimatedPanel>
            <div className="admin-card-title">GST & billing</div>
            <form onSubmit={save} className="admin-form-grid">
              <label>
                GSTIN
                <input className="admin-input gst-mono" value={gstin} onChange={(e) => setGstin(e.target.value)} placeholder="27AABCU9603R1ZM" />
              </label>
              <label>
                Place of supply
                <input className="admin-input" value={placeOfSupply} onChange={(e) => setPlaceOfSupply(e.target.value)} placeholder="Maharashtra" />
              </label>
              <span className="admin-badge admin-badge-active">Used on tax invoices</span>
              <button type="submit" className="admin-btn admin-btn-primary">Save changes</button>
              {saved && <p className="admin-job-msg">Settings saved.</p>}
            </form>
            <p style={{ marginTop: "1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
              Need to import past sales data? Go to <Link to="/store/reports">Import / Export</Link>.
            </p>
          </AnimatedPanel>
        </StaggerItem>
      </StaggerGrid>
    </AppShell>
  );
}
