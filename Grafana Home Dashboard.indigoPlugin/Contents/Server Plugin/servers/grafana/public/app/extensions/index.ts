import { config, featureEnabled, reportExperimentView } from '@grafana/runtime';
import { contextSrv } from 'app/core/core';
import { extraRoutes } from 'app/routes/routes';
import { addRootReducer } from 'app/store/configureStore';
import { AccessControlAction, DashboardRoutes } from 'app/types';

import { initEnterpriseAdmin } from './admin';
import { initPageBanners } from './banners';
import DataSourceCache from './caching/DataSourceCache';
import DataSourceCacheUpgradePage from './caching/UpgradePage';
import dataSourceCacheReducers from './caching/state/reducers';
import { initLicenseWarnings } from './licensing';
import LicensePage from './licensing/LicensePage';
import { initMetaAnalytics } from './meta-analytics';
import DataSourceInsights from './meta-analytics/DataSourceInsights/DataSourceInsights';
import DataSourceInsightsUpgradePage from './meta-analytics/DataSourceInsights/UpgradePage';
import metaAnalyticsReducers from './meta-analytics/state/reducers';
import DatasourcePermissions from './permissions/AccessControlDataSourcePermissions';
import LegacyDataSourcePermissions from './permissions/DataSourcePermissions';
import DatasourcePermissionsUpgradePage from './permissions/UpgradePage';
import dataSourcePermissionReducers from './permissions/state/reducers';
import { initRecordedQueries } from './recorded-queries';
import { RecordedQueriesConfig } from './recorded-queries/RecordedQueriesConfig';
import { WriteTargetConfig } from './recorded-queries/WriteTargetConfig';
import { recordedQueryReducer } from './recorded-queries/state/reducers';
import { initReporting, reportSteps } from './reports';
import CSVExportPage from './reports/CSVExportPage';
import Confirm from './reports/ReportForm/Confirm';
import SelectDashboard from './reports/ReportForm/SelectDashboard';
import ReportsList from './reports/ReportsListPage';
import ReportsSettings from './reports/ReportsSettingsPage';
import ReportsUpgrade from './reports/ReportsUpgradePage';
import { BASE_URL as REPORTS_BASE } from './reports/constants';
import reportsReducers from './reports/state/reducers';
import { AccessControlAction as EnterpriseAccessControlAction } from './types';
import { buildExperimentID, ExperimentGroup } from './utils/featureHighlights';
import { initWhitelabeling } from './whitelabeling';

export function addExtensionReducers() {
  if (featureEnabled('dspermissions')) {
    addRootReducer(dataSourcePermissionReducers);
  }

  if (featureEnabled('caching')) {
    addRootReducer(dataSourceCacheReducers);
  }

  if (featureEnabled('reports')) {
    addRootReducer(reportsReducers);
  }

  if (featureEnabled('analytics')) {
    addRootReducer(metaAnalyticsReducers);
  }

  if (featureEnabled('recordedqueries')) {
    addRootReducer(recordedQueryReducer);
  }
}

function initEnterprise() {
  const highlightsEnabled = config.featureToggles.featureHighlights;
  initLicenseWarnings();
  initReporting();
  initMetaAnalytics();

  if (featureEnabled('whitelabeling')) {
    initWhitelabeling();
  }

  if (featureEnabled('recordedqueries')) {
    initRecordedQueries();
  }

  if (featureEnabled('admin')) {
    initEnterpriseAdmin();
  }

  // DataSources components
  if (featureEnabled('caching')) {
    extraRoutes.push({
      path: '/datasources/edit/:uid/cache',
      component: DataSourceCache,
    });
  } else if (highlightsEnabled) {
    extraRoutes.push({
      path: '/datasources/edit/:uid/cache/upgrade',
      component: DataSourceCacheUpgradePage,
    });
  }

  if (featureEnabled('analytics')) {
    extraRoutes.push({
      path: '/datasources/edit/:uid/insights',
      component: DataSourceInsights as any,
    });
  } else if (highlightsEnabled) {
    extraRoutes.push({
      path: '/datasources/edit/:uid/insights/upgrade',
      component: DataSourceInsightsUpgradePage,
    });
  }

  const permissionsPath = '/datasources/edit/:uid/permissions';
  if (featureEnabled('dspermissions') && contextSrv.hasPermission(AccessControlAction.DataSourcesPermissionsRead)) {
    if (config.featureToggles['accesscontrol']) {
      extraRoutes.push({
        path: permissionsPath,
        component: DatasourcePermissions,
      });
    } else {
      extraRoutes.push({
        path: permissionsPath,
        component: LegacyDataSourcePermissions,
      });
    }
  } else if (highlightsEnabled) {
    extraRoutes.push({
      path: permissionsPath + '/upgrade',
      component: DatasourcePermissionsUpgradePage,
    });
  }

  if (config.reporting?.enabled) {
    if (featureEnabled('reports')) {
      extraRoutes.push(
        {
          path: REPORTS_BASE,
          component: ReportsList,
        },
        {
          path: `${REPORTS_BASE}/edit/:id`,
          component: Confirm,
        },
        {
          path: `${REPORTS_BASE}/settings`,
          component: ReportsSettings,
        },
        {
          path: '/d-csv/:uid',
          pageClass: 'dashboard-solo',
          routeName: DashboardRoutes.Normal,
          component: CSVExportPage,
        }
      );
    } else if (highlightsEnabled) {
      extraRoutes.push({
        path: REPORTS_BASE,
        component: ReportsUpgrade,
      });
    }

    if (featureEnabled('reports.creation')) {
      extraRoutes.push({
        path: `${REPORTS_BASE}/new`,
        component: SelectDashboard,
      });

      for (const step of reportSteps) {
        extraRoutes.push({ path: `${REPORTS_BASE}/${step.id}`, component: step.component });
      }
    }
  }

  const showRecordQuery = featureEnabled('recordedqueries') && config?.recordedQueries?.enabled;
  if (contextSrv.isEditor && showRecordQuery) {
    extraRoutes.push(
      ...[
        {
          path: '/recorded-queries',
          component: RecordedQueriesConfig,
        },
        {
          path: '/recorded-queries/write-target',
          component: WriteTargetConfig,
        },
      ]
    );
  }
}

// initUnlicensed initialized features which are defined in Enterprise but
// should be available when running without a license.
function initUnlicensed() {
  initPageBanners();

  extraRoutes.push({
    path: '/admin/licensing',
    roles: () =>
      contextSrv.evaluatePermission(
        () => ['ServerAdmin'],
        [EnterpriseAccessControlAction.LicensingRead, AccessControlAction.ActionServerStatsRead]
      ),
    component: LicensePage,
  });

  // Report experimentation views
  if (contextSrv.isSignedIn && config.licenseInfo.stateInfo !== 'Licensed') {
    reportExperimentView(
      buildExperimentID(),
      config.featureToggles.featureHighlights ? ExperimentGroup.Test : ExperimentGroup.Control,
      ''
    );
  }
}

export function init() {
  initUnlicensed();
  initEnterprise();
}
