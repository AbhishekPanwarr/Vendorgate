import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { AppShell } from './components/layout/AppShell';
import { DashboardPage } from './pages/DashboardPage';
import { SubmitPage } from './pages/SubmitPage';
import { RunsPage } from './pages/RunsPage';
import { CaseDetailPage } from './pages/CaseDetailPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { VendorsPage } from './pages/VendorsPage';
import { BenchmarkPage } from './pages/BenchmarkPage';
import { PolicyPage } from './pages/PolicyPage';
import { FoolItPage } from './pages/FoolItPage';
import { AdminPage } from './pages/AdminPage';

const RouterView: React.FC = () => {
  const { currentPath } = useApp();

  if (currentPath === '/' || currentPath === '/dashboard') {
    return <DashboardPage />;
  }

  if (currentPath === '/submit') {
    return <SubmitPage />;
  }

  if (currentPath.startsWith('/runs')) {
    const parts = currentPath.split('/');
    const runId = parts[2] || undefined;
    return <RunsPage runIdProp={runId} />;
  }

  if (currentPath.startsWith('/cases')) {
    const parts = currentPath.split('/');
    const caseId = parts[2] || undefined;
    return <CaseDetailPage caseIdProp={caseId} />;
  }

  if (currentPath.startsWith('/approvals')) {
    return <ApprovalsPage />;
  }

  if (currentPath.startsWith('/vendors')) {
    return <VendorsPage />;
  }

  if (currentPath.startsWith('/benchmark')) {
    return <BenchmarkPage />;
  }

  if (currentPath.startsWith('/policy')) {
    return <PolicyPage />;
  }

  if (currentPath.startsWith('/foolit') || currentPath.startsWith('/fool-it')) {
    return <FoolItPage />;
  }

  if (currentPath.startsWith('/admin')) {
    return <AdminPage />;
  }

  // Fallback to Dashboard
  return <DashboardPage />;
};

export default function App() {
  return (
    <AppProvider>
      <AppShell>
        <RouterView />
      </AppShell>
    </AppProvider>
  );
}
