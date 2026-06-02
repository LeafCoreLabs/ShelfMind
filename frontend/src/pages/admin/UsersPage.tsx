import { useEffect, useState } from "react";
import AppShell from "../../components/layout/AppShell";
import { adminApi } from "../../api/admin";
import { User } from "../../api/client";
import { ADMIN_SHELL } from "./adminShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import { AnimatedTableBody, AnimatedTableRow } from "../../components/motion/AnimatedTable";
import "./admin-theme.css";

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");

  const load = () => adminApi.getUsers({ search: search || undefined }).then((r) => setUsers(r.users));

  useEffect(() => {
    load();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    load();
  };

  const deactivate = async (id: number) => {
    await adminApi.deactivateUser(id);
    load();
  };

  return (
    <AppShell
      {...ADMIN_SHELL}
      title="Users"
      subtitle="Manage store-owner accounts across the platform"
    >
      <form className="admin-search-row" onSubmit={handleSearch}>
        <input
          className="admin-input"
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit" className="admin-btn admin-btn-primary">
          Search
        </button>
      </form>

      <AnimatedPanel className="admin-card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="admin-table-modern">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Store</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <AnimatedTableBody dataKey={users.length}>
            {users.map((u, i) => (
              <AnimatedTableRow key={u.id} index={i}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <span className={`admin-badge ${u.role === "admin" ? "admin-badge-warning" : "admin-badge-active"}`}>
                    {u.role}
                  </span>
                </td>
                <td>{u.store_id ?? "—"}</td>
                <td>
                  <span className={`admin-badge ${u.is_active ? "admin-badge-active" : "admin-badge-inactive"}`}>
                    {u.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  {u.is_active && u.role !== "admin" && (
                    <button type="button" className="admin-btn admin-btn-sm admin-btn-danger" onClick={() => deactivate(u.id)}>
                      Deactivate
                    </button>
                  )}
                </td>
              </AnimatedTableRow>
            ))}
          </AnimatedTableBody>
        </table>
      </AnimatedPanel>
    </AppShell>
  );
}
