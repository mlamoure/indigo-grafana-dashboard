import { SelectableValue } from '@grafana/data';
import { DashboardPickerItem } from 'app/core/components/editors/DashboardPickerByID';

export const daysOfMonth: Array<SelectableValue<string>> = Array.from(Array(31), (_, i) => {
  const value = (i + 1).toString();
  return { value, label: value };
});
daysOfMonth.unshift({ value: 'last', label: 'Last' });

export const daysOfWeek: Array<SelectableValue<string>> = [
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
  { value: 'saturday', label: 'Saturday' },
  { value: 'sunday', label: 'Sunday' },
];

export interface ReportsState {
  reports: Report[];
  report: Report;
  hasFetchedList: boolean;
  hasFetchedSingle: boolean;
  searchQuery: string;
  reportCount: number;
  isLoading: boolean;
  settings: ReportsSettings;
  testEmailIsSending?: boolean;
  lastUid?: string;
  isUpdated?: boolean;
  visitedSteps: StepKey[];
}

export interface Report<Vars = Record<string, string>> {
  id: number;
  name: string;
  schedule: SchedulingOptions;
  dashboardId?: number;
  dashboardUid?: string;
  dashboardName?: string;
  recipients: string;
  message: string;
  replyTo: string;
  options: ReportOptions;
  templateVars?: Vars;
  enableDashboardUrl?: boolean;
  enableCsv?: boolean;
  state?: ReportState;
}

interface ReportBase<Vars = Record<string, string>> {
  id?: number;
  name: string;
  dashboardId?: number;
  dashboardUid?: string;
  recipients: string;
  replyTo: string;
  message: string;
  options: ReportOptions;
  templateVars?: Vars;
  enableDashboardUrl?: boolean;
  enableCsv?: boolean;
  state?: ReportState;
}

export interface ReportDTO extends ReportBase {
  schedule: SchedulingOptions;
}

export interface ReportFormData extends ReportBase<Record<string, Array<SelectableValue<string>>>> {
  schedule: SchedulingData;
  dashboard: DashboardPickerItem;
}

export enum SchedulingFrequency {
  Monthly = 'monthly',
  Weekly = 'weekly',
  Daily = 'daily',
  Hourly = 'hourly',
  Never = 'never',
  Custom = 'custom',
  Once = 'once',
}

export enum IntervalFrequency {
  Hours = 'hours',
  Days = 'days',
  Weeks = 'weeks',
  Months = 'months',
}

export enum FooterMode {
  Default = '',
  SentBy = 'sent-by',
  None = 'none',
}

export enum ReportState {
  Paused = 'paused',
  Scheduled = 'scheduled',
  Expired = 'expired',
  Draft = 'draft',
  Never = 'not scheduled',
}

export type ReportTime = {
  hour: number;
  minute: number;
};

export interface SchedulingOptions {
  frequency: SchedulingFrequency;
  dayOfMonth?: string;
  timeZone: string;
  startDate?: string;
  endDate?: string;
  intervalFrequency?: IntervalFrequency;
  intervalAmount?: number;
  workdaysOnly?: boolean;
}

export interface SchedulingData {
  frequency: SchedulingFrequency;
  dayOfMonth?: boolean;
  time?: ReportTime;
  endTime?: ReportTime;
  timeZone: string;
  startDate?: Date | string;
  endDate?: Date | string;
  intervalFrequency?: IntervalFrequency;
  intervalAmount?: string;
  workdaysOnly?: boolean;
  sendTime: string;
}

export type ReportOrientation = 'portrait' | 'landscape';

export type ReportLayout = 'simple' | 'grid';

export interface BrandingOptions {
  reportLogoUrl: string;
  emailLogoUrl: string;
  emailFooterMode: FooterMode;
  emailFooterText: string;
  emailFooterLink: string;
}

export interface ReportsSettings {
  branding: BrandingOptions;
}

export interface ReportOptions {
  orientation: ReportOrientation;
  layout: ReportLayout;
  timeRange: ReportTimeRange;
}

export interface ReportTimeRange {
  from: string;
  to: string;
  raw?: ReportTimeRange;
}

export const reportOrientations: Array<SelectableValue<ReportOrientation>> = [
  { value: 'landscape', label: 'Landscape', icon: 'gf-landscape' },
  { value: 'portrait', label: 'Portrait', icon: 'gf-portrait' },
];

export const reportLayouts: Array<SelectableValue<ReportLayout>> = [
  { value: 'grid', label: 'Grid', icon: 'gf-grid' },
  { value: 'simple', label: 'Simple', icon: 'gf-layout-simple' },
];

export enum StepKey {
  SelectDashboard = 'select-dashboard',
  StyleReport = 'style-report',
  Schedule = 'schedule',
  Share = 'share',
  Confirm = 'confirm',
}

export type FormRequiredFields = Array<{
  step: StepKey;
  fields: Array<keyof Report>;
}>;
