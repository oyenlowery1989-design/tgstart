import Sidebar from "./Sidebar.jsx";

export default function Layout({ children }) {
  return (
    <div className="flex bg-slate-950 text-slate-100">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
