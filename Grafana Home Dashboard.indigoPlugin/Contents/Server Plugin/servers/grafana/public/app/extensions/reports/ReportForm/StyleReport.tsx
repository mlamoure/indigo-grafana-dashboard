import React from 'react';
import { useForm } from 'react-hook-form';
import { connect, ConnectedProps } from 'react-redux';

import { AppEvents, urlUtil } from '@grafana/data';
import { featureEnabled, reportInteraction } from '@grafana/runtime';
import { Checkbox, Field, FieldSet, LinkButton, RadioButtonGroup, InputControl } from '@grafana/ui';
import { appEvents } from 'app/core/core';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';
import { getVariablesByKey } from 'app/features/variables/state/selectors';

import {
  EnterpriseStoreState,
  ReportFormData,
  ReportLayout,
  reportLayouts,
  reportOrientations,
  StepKey,
} from '../../types';
import { getRange } from '../../utils/time';
import { updateReportProp } from '../state/reducers';
import { getLastUid } from '../state/selectors';
import { canEditReport } from '../utils/permissions';
import { getRendererMajorVersion } from '../utils/renderer';
import { variablesToCsv } from '../utils/variables';

import ReportForm from './ReportForm';

interface OwnProps extends GrafanaRouteComponentProps<{ id: string }> {}

const mapStateToProps = (state: EnterpriseStoreState) => {
  const lastUid = getLastUid(state);
  return {
    report: state.reports.report,
    variables: lastUid ? getVariablesByKey(lastUid) : [],
  };
};

const mapActionsToProps = {
  updateReportProp,
};

const connector = connect(mapStateToProps, mapActionsToProps);
export type Props = ConnectedProps<typeof connector> & OwnProps;

const descriptions = new Map<ReportLayout, string>([
  ['grid', 'Display the panels in their positions on the dashboard.'],
  ['simple', 'Display one panel per row.'],
]);

export const StyleReport = ({ report, variables, updateReportProp }: Props) => {
  const {
    handleSubmit,
    control,
    register,
    watch,
    formState: { isDirty },
  } = useForm();
  const { dashboardId, enableCsv, options, name } = report || {};
  const orientation = options.orientation || 'landscape';
  const layout = options.layout || 'grid';
  const watchLayout = watch('options.layout', layout);
  const watchOrientation = watch('options.orientation', orientation);
  const rendererMajorVersion = getRendererMajorVersion();

  const saveData = ({ enableCsv, options }: Partial<ReportFormData>) => {
    if (isDirty) {
      updateReportProp({ ...report, options: { ...report.options, ...options }, enableCsv });
    }
  };

  const getPreviewUrl = (dashboardId: ReportFormData['dashboardId']) => {
    if (!dashboardId) {
      return undefined;
    }

    const { from, to } = getRange(options.timeRange).raw;

    const params: any = {
      title: name,
      from: from.valueOf(),
      to: to.valueOf(),
    };

    if (watchOrientation) {
      params.orientation = watchOrientation;
    }

    if (watchLayout) {
      params.layout = watchLayout;
    }

    if (variables?.length) {
      params.variables = JSON.stringify(variablesToCsv(variables));
    }

    return urlUtil.appendQueryToUrl(`api/reports/render/pdf/${dashboardId}`, urlUtil.toUrlParams(params));
  };

  return (
    <ReportForm activeStep={StepKey.StyleReport} onSubmit={handleSubmit(saveData)} confirmRedirect={isDirty}>
      <FieldSet label={'2. Style report'} disabled={!canEditReport}>
        <Field label="Orientation">
          <InputControl
            name={'options.orientation'}
            control={control}
            defaultValue={orientation}
            render={({ field: { ref, ...field } }) => {
              return <RadioButtonGroup {...field} options={reportOrientations} size={'md'} />;
            }}
          />
        </Field>
        <Field label="Layout" description={descriptions.get(watchLayout)}>
          <InputControl
            name={'options.layout'}
            control={control}
            defaultValue={layout}
            render={({ field: { ref, ...field } }) => {
              return <RadioButtonGroup {...field} options={reportLayouts} size={'md'} />;
            }}
          />
        </Field>

        <Field disabled={!canEditReport}>
          <Checkbox
            {...register('enableCsv')}
            defaultChecked={enableCsv}
            label="Add a CSV file of table panel data"
            onChange={(event: React.FormEvent<HTMLInputElement>) => {
              const enabled = event.currentTarget.checked;
              if (enabled && rendererMajorVersion !== null && rendererMajorVersion < 3) {
                appEvents.emit(AppEvents.alertError, [
                  'To export CSV files, you must update the Grafana Image Renderer plugin.',
                ]);
              }
            }}
          />
        </Field>
        <Field disabled={!featureEnabled('reports.email') || !dashboardId}>
          <LinkButton
            onClick={() => {
              reportInteraction('reports_preview_pdf');
            }}
            icon={'external-link-alt'}
            href={getPreviewUrl(dashboardId)}
            size="xs"
            target="_blank"
            rel="noreferrer noopener"
            variant="secondary"
          >
            Preview PDF
          </LinkButton>
        </Field>
      </FieldSet>
    </ReportForm>
  );
};

export default connector(StyleReport);
