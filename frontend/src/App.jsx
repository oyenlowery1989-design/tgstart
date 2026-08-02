import Layout from "./components/Layout.jsx";
import StatsPage from "./pages/StatsPage.jsx";
import ReplyPage from "./pages/ReplyPage.jsx";

export default function App() {
  const isReply = window.location.pathname === "/app/reply";
  return <Layout>{isReply ? <ReplyPage /> : <StatsPage />}</Layout>;
}
