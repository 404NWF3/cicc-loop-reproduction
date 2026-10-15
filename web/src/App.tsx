import { useEffect } from 'react';
import { Link, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { SiteFooter, SiteHeader } from './components';
import { ExperimentsPage, HomePage, ResearchPage } from './pages/ResearchPages';
import { LivePage } from './pages/LivePage';
import { PresentationPage } from './pages/PresentationPage';
import {
  ConsoleLayout,
  ConsolePage,
  FactorPage,
  RunPage,
  SettingsPage,
} from './pages/ConsolePages';

function SiteLayout() {
  return (
    <>
      <SiteHeader />
      <Outlet />
      <SiteFooter />
    </>
  );
}

export default function App() {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  return (
    <>
      <a className="skip-link" href="#main-content">
        跳至主要内容
      </a>
      <div id="main-content">
        <Routes>
          <Route path="presentation" element={<PresentationPage />} />
          <Route element={<SiteLayout />}>
            <Route index element={<HomePage />} />
            <Route path="research" element={<ResearchPage />} />
            <Route path="experiments" element={<ExperimentsPage />} />
            <Route path="mine" element={<LivePage />} />
            <Route path="mine/:runId" element={<LivePage />} />
          </Route>
          <Route path="console" element={<ConsoleLayout />}>
            <Route index element={<ConsolePage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="runs/:runId" element={<RunPage />} />
            <Route path="factors/:factorId" element={<FactorPage />} />
          </Route>
          <Route
            path="*"
            element={
              <div className="not-found">
                <h1>没有找到这个页面</h1>
                <Link className="button navy" to="/">
                  回到研究概览
                </Link>
              </div>
            }
          />
        </Routes>
      </div>
    </>
  );
}
