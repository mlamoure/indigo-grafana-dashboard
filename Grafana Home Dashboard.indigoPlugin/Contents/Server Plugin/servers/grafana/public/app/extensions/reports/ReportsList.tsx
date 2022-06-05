import { css, cx } from '@emotion/css';
import React, { FC } from 'react';

import { GrafanaTheme2 } from '@grafana/data';
import { Button, CardContainer, ConfirmButton, Tooltip, useStyles2, useTheme2 } from '@grafana/ui';
import { contextSrv } from 'app/core/core';

import { AccessControlAction, Report, ReportState } from '../types';

import { getReportState, getReportStateInfo } from './utils/reportState';
import { parseScheduleTime } from './utils/scheduler';

interface Props {
  reports: Report[];
  deleteReport: (report: Report) => void;
  updateReport: (report: Report) => void;
  filter: string;
}

const filterReports = (reports: Report[], filter: string) => {
  const filterFields: Array<keyof Pick<Report, 'name' | 'dashboardName' | 'recipients'>> = [
    'name',
    'dashboardName',
    'recipients',
  ];

  return reports.filter((report) => {
    return filterFields.some((field) => report[field]?.toLowerCase().includes(filter.toLowerCase()));
  });
};

const getReportStateColors = (theme: GrafanaTheme2) => {
  return new Map([
    [ReportState.Scheduled, theme.colors.success.text],
    [ReportState.Expired, theme.colors.warning.text],
    [ReportState.Draft, theme.colors.text.secondary],
    [ReportState.Never, theme.colors.text.secondary],
    [ReportState.Paused, theme.colors.text.disabled],
  ]);
};

export const ReportList: FC<Props> = ({ deleteReport, updateReport, reports, filter }) => {
  const theme = useTheme2();
  const styles = useStyles2(getStyles);

  const toggleReportState = (report: Report) => {
    const state = getReportState(report);
    let newState;

    if ([ReportState.Draft, ReportState.Expired].includes(state)) {
      newState = state;
    } else if (state !== ReportState.Paused) {
      newState = ReportState.Paused;
    } else {
      newState = ReportState.Scheduled;
    }

    updateReport({
      ...report,
      state: newState,
    });
  };

  const canEditReport = contextSrv.hasPermission(AccessControlAction.ReportingAdminWrite);
  const canDeleteReport = contextSrv.hasPermission(AccessControlAction.ReportingDelete);

  return (
    <div>
      {filterReports(reports, filter).map((report) => {
        const splitRecipients = report.recipients.split(';');
        const numRecipients = splitRecipients.length;
        const scheduleTime = parseScheduleTime(report.schedule);
        const { isNever, showPlay, disableEdit, reportState } = getReportStateInfo(report);
        const color = getReportStateColors(theme).get(reportState);
        return (
          <CardContainer key={report.id} href={`reports/edit/${report.id}`} className={styles.container}>
            <div className={styles.info}>
              <span className={styles.title}>{report.name}</span>
              <span>{report.dashboardName}</span>
            </div>
            <div className={styles.recipients}>
              <Tooltip content={splitRecipients.join(', ')} placement={'top'}>
                <div>{`${numRecipients} recipient${numRecipients > 1 ? 's' : ''}`}</div>
              </Tooltip>
            </div>
            <div className={styles.schedule}>
              <span
                className={cx(
                  styles.scheduleStatus,
                  css`
                    color: ${color};
                  `
                )}
              >
                {reportState.toUpperCase()}
              </span>
              {!isNever && <span className={getTextColor(theme, reportState)}>{scheduleTime}</span>}
            </div>
            <div className={styles.buttonWrapper}>
              <Tooltip content={`${showPlay ? 'Resume' : 'Pause'} report`} placement={'top'}>
                <Button
                  type={'button'}
                  variant={'secondary'}
                  fill={'text'}
                  icon={showPlay ? 'play' : 'pause'}
                  size={'md'}
                  onClick={(e) => {
                    e.preventDefault();
                    toggleReportState(report);
                  }}
                  disabled={disableEdit || !canEditReport}
                />
              </Tooltip>
              <ConfirmButton
                confirmText="Delete"
                confirmVariant="destructive"
                size={'md'}
                disabled={!canDeleteReport}
                onConfirm={() => deleteReport(report)}
              >
                <Button
                  type="button"
                  className={styles.deleteButton}
                  aria-label={`Delete report ${report.name}`}
                  variant="secondary"
                  icon="trash-alt"
                  size={'md'}
                  fill={'text'}
                />
              </ConfirmButton>
            </div>
          </CardContainer>
        );
      })}
    </div>
  );
};

const getTextColor = (theme: GrafanaTheme2, reportState: ReportState) => {
  return css`
    color: ${[ReportState.Scheduled, ReportState.Draft].includes(reportState)
      ? theme.colors.text.primary
      : theme.colors.text.secondary};
  `;
};
const getStyles = (theme: GrafanaTheme2) => {
  return {
    container: css`

    & > a {
        align-items: center;
      },
    `,
    info: css`
      display: flex;
      flex-direction: column;
      width: 30%;
    `,
    title: css`
      font-size: ${theme.typography.h5.fontSize};
      font-weight: ${theme.typography.fontWeightBold};
    `,
    recipients: css`
      display: flex;
      width: 25%;
      cursor: pointer;

      &:hover {
        text-decoration: underline;
      },
    `,
    schedule: css`
      display: flex;
      flex-direction: column;
      width: 40%;
    `,
    scheduleStatus: css`
      text-transform: uppercase;
    `,
    buttonWrapper: css`
      display: flex;
      align-items: center;
      width: 5%;
      & > button {
        &[disabled] {
          pointer-events: all;
        },
      },
    `,
    deleteButton: css`
      &:hover {
        color: ${theme.colors.error.text};
    `,
  };
};
