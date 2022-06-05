import { featureEnabled } from '@grafana/runtime';
import { ProBadge } from 'app/core/components/Upgrade/ProBadge';
import { config } from 'app/core/config';
import { contextSrv } from 'app/core/services/context_srv';
import { highlightTrial } from 'app/features/admin/utils';
import { addDashboardShareTab, ShareModalTabModel } from 'app/features/dashboard/components/ShareModal';

import { AccessControlAction, StepKey } from '../types';
import { buildExperimentID } from '../utils/featureHighlights';

import { CreateReportTab } from './CreateReportTab';
import Confirm from './ReportForm/Confirm';
import Schedule from './ReportForm/Schedule';
import SelectDashboard from './ReportForm/SelectDashboard';
import Share from './ReportForm/Share';
import StyleReport from './ReportForm/StyleReport';
import { SharePDF } from './SharePDF';

const highlightsEnabled = config.featureToggles.featureHighlights;
const sharePDFTab: ShareModalTabModel = {
  label: 'PDF',
  value: 'pdf',
  component: SharePDF,
};

const createReportTab: ShareModalTabModel = {
  label: 'Report',
  value: 'report',
  tabSuffix:
    (highlightsEnabled && !featureEnabled('reports.creation')) || highlightTrial()
      ? () => ProBadge({ experimentId: buildExperimentID('reporting-tab-badge') })
      : undefined,
  component: CreateReportTab,
};

export function initReporting() {
  if (!config.reporting?.enabled) {
    return;
  }

  if (featureEnabled('reports.creation')) {
    addDashboardShareTab(sharePDFTab);

    if (contextSrv.hasAccess(AccessControlAction.ReportingAdminCreate, contextSrv.hasRole('Admin'))) {
      addDashboardShareTab(createReportTab);
    }
  } else if (highlightsEnabled) {
    addDashboardShareTab(createReportTab);
  }
}

export const reportSteps = [
  { id: StepKey.SelectDashboard, name: 'Select dashboard', component: SelectDashboard },
  { id: StepKey.StyleReport, name: 'Style report', component: StyleReport },
  { id: StepKey.Schedule, name: 'Schedule', component: Schedule },
  { id: StepKey.Share, name: 'Share', component: Share },
  { id: StepKey.Confirm, name: 'Confirm', component: Confirm },
];
