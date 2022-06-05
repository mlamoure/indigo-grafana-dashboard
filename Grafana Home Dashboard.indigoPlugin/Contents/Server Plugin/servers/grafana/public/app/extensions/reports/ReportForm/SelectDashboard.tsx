import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { connect, ConnectedProps } from 'react-redux';

import { Field, FieldSet, InlineField, InputControl, TimeRangeInput } from '@grafana/ui';
import { DashboardPickerByID, DashboardPickerItem } from 'app/core/components/editors/DashboardPickerByID';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';
import { variableAdapters } from 'app/features/variables/adapters';
import { hasOptions } from 'app/features/variables/guard';
import { cleanUpVariables } from 'app/features/variables/state/actions';
import { getVariablesByKey } from 'app/features/variables/state/selectors';
import { VariableModel } from 'app/features/variables/types';

import { EnterpriseStoreState, ReportFormData, StepKey } from '../../types';
import { getRange, parseRange } from '../../utils/time';
import { initVariables } from '../state/actions';
import { updateReportProp } from '../state/reducers';
import { getLastUid } from '../state/selectors';
import { canEditReport } from '../utils/permissions';
import { applyUrlValues, getUrlValues } from '../utils/url';
import { variablesToCsv } from '../utils/variables';

import ReportForm from './ReportForm';

interface OwnProps extends GrafanaRouteComponentProps<{ id: string }> {}

const mapStateToProps = (state: EnterpriseStoreState) => {
  const lastUid = getLastUid(state);
  const { report } = state.reports;
  return {
    report,
    variables: lastUid ? getVariablesByKey(lastUid) : [],
    lastUid,
  };
};

const mapActionsToProps = {
  updateReportProp,
  initVariables,
  cleanUpVariables,
};

const connector = connect(mapStateToProps, mapActionsToProps);
export type Props = ConnectedProps<typeof connector> & OwnProps;

export const SelectDashboard = ({
  report,
  updateReportProp,
  variables,
  initVariables,
  cleanUpVariables,
  lastUid,
}: Props) => {
  const {
    handleSubmit,
    control,
    setValue,
    formState: { isDirty },
    watch,
  } = useForm();
  const { dashboardId, dashboardName, dashboardUid, options } = applyUrlValues(report);
  const currentDashboard =
    (dashboardId || 0) > 0
      ? ({ value: dashboardId, id: dashboardId, uid: dashboardUid, label: dashboardName } as DashboardPickerItem)
      : undefined;
  const timeRange = getRange(options.timeRange);
  const watchDashboard = watch('dashboard', currentDashboard);

  useEffect(() => {
    const urlValues = getUrlValues();

    if (!urlValues) {
      return;
    }
    if (urlValues.dashboard.uid) {
      setValue('dashboard', currentDashboard, { shouldDirty: true });
    }
    // If new report is created, apply the values from URL params for variables
    const { dashboard, variables } = urlValues;
    if (variables && dashboard.uid) {
      initVariables(dashboard.uid, variables);
    }

    //eslint-disable-next-line
  }, []);

  const onDashboardChange = (dashboard?: DashboardPickerItem) => {
    // Reset time range when dashboard changes
    setValue('options.timeRange', { from: '', to: '' });
    if (!dashboard) {
      if (lastUid) {
        cleanUpVariables(lastUid);
      }
      return;
    }
    if (dashboard.uid) {
      const defaultVars = dashboard.id === report.dashboardId ? report.templateVars : undefined;
      initVariables(dashboard.uid, defaultVars);
    }
  };

  const saveData = (data: Partial<ReportFormData>) => {
    const dto = {
      dashboardUid: data?.dashboard?.uid,
      dashboardId: data?.dashboard?.id,
      dashboardName: data?.dashboard?.label,
      templateVars: variablesToCsv(variables),
      options: {
        ...report.options,
        timeRange: parseRange(data.options?.timeRange?.raw),
      },
    };

    if (isDirty) {
      updateReportProp({ ...report, ...dto });
    }
  };

  return (
    <ReportForm activeStep={StepKey.SelectDashboard} onSubmit={handleSubmit(saveData)} confirmRedirect={isDirty}>
      <FieldSet label={'1. Select dashboard'}>
        <Field label="Source dashboard" required>
          <InputControl
            name="dashboard"
            control={control}
            defaultValue={currentDashboard}
            render={({ field: { onChange, ref, ...field } }) => {
              return (
                <DashboardPickerByID
                  {...field}
                  aria-label={'Source dashboard'}
                  isClearable
                  disabled={!canEditReport}
                  onChange={(dashboard) => {
                    onDashboardChange(dashboard);
                    onChange(dashboard);
                  }}
                />
              );
            }}
          />
        </Field>
        {watchDashboard?.id !== undefined && Boolean(variables.length) && (
          <Field label={'Template variables'}>
            <>
              {variables.map((variable) => {
                const { picker: Picker, setValue: updateVariable } = variableAdapters.get(variable.type);
                return (
                  <InlineField label={variable.name} key={variable.name} labelWidth={16} disabled={!canEditReport}>
                    <Picker
                      variable={variable}
                      onVariableChange={(updated: VariableModel) => {
                        if (hasOptions(updated)) {
                          updateVariable(updated, updated.current);
                          setValue('templateVars', updated, { shouldDirty: true });
                        }
                      }}
                    />
                  </InlineField>
                );
              })}
            </>
          </Field>
        )}
        <Field
          label="Time range"
          description="Generate report with the data from specified time range. If custom time range is empty the time range from the report's dashboard is used."
          disabled={!canEditReport}
        >
          <InputControl
            control={control}
            name={'options.timeRange'}
            defaultValue={timeRange}
            render={({ field: { ref, ...field } }) => {
              return <TimeRangeInput {...field} clearable />;
            }}
          />
        </Field>
      </FieldSet>
    </ReportForm>
  );
};

export default connector(SelectDashboard);
