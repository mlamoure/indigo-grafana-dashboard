import { FormRequiredFields, StepKey } from '../types';

export const defaultReportLogo = '/public/img/grafana_icon.svg';
export const defaultEmailLogo = 'https://grafana.com/static/assets/img/grafana_logo_lockup_ltbg.png';

export const BASE_URL = '/reports';

export const requiredFields: FormRequiredFields = [
  { step: StepKey.SelectDashboard, fields: ['dashboardName'] },
  { step: StepKey.Share, fields: ['name', 'recipients'] },
];
