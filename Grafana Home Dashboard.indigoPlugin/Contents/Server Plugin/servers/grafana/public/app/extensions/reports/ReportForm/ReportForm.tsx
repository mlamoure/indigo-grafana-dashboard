import { css } from '@emotion/css';
import React, { useEffect, useRef } from 'react';
import { connect, ConnectedProps } from 'react-redux';
import { useHistory } from 'react-router-dom';

import { GrafanaTheme2 } from '@grafana/data';
import { Button, useStyles2 } from '@grafana/ui';

import { EnterpriseStoreState, StepKey } from '../../types';
import { BASE_URL } from '../constants';
import { reportSteps } from '../index';
import { clearReportState, addVisitedStep } from '../state/reducers';
import { getNextStep, getPreviousStep, goToPreviousStep } from '../utils/stepper';

import { ReportFormPrompt } from './ReportFormPrompt';
import { ReportPageContainer } from './ReportPageContainer';
import Stepper from './Stepper';

const mapStateToProps = (state: EnterpriseStoreState) => {
  const { report, isUpdated } = state.reports;
  return {
    report,
    existingReport: !!report.id,
    isUpdated,
  };
};

const mapActionsToProps = {
  clearReportState,
  addVisitedStep,
};

export interface OwnProps {
  children: React.ReactNode;
  activeStep: StepKey;
  onSubmit: () => void;
  disabled?: boolean;
  editMode?: boolean;
  confirmRedirect?: boolean;
}

const connector = connect(mapStateToProps, mapActionsToProps);
export type Props = ConnectedProps<typeof connector> & OwnProps;

export const ReportForm = ({
  children,
  activeStep,
  onSubmit,
  disabled,
  editMode,
  existingReport,
  clearReportState,
  addVisitedStep,
  confirmRedirect,
  isUpdated,
  report,
}: Props) => {
  const styles = useStyles2(getStyles);
  const nextStep = getNextStep(activeStep);
  const previousStep = getPreviousStep(activeStep);
  const isLastStep = nextStep.id === activeStep;
  const history = useHistory();
  const buttonText = isLastStep ? (existingReport ? 'Update report' : 'Save report') : `Next: ${nextStep.name}`;
  const hideSteps = editMode && isLastStep;
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const addStep = (step: StepKey) => {
      if (step === reportSteps[reportSteps.length - 1].id) {
        addVisitedStep(reportSteps.map((step) => step.id));
      } else {
        addVisitedStep([step]);
      }
    };
    addStep(activeStep);
  }, [activeStep, addVisitedStep]);

  const onStepChange = () => {
    const lastId = reportSteps[reportSteps.length - 1].id;
    // Do not submit for the last step
    if (activeStep !== lastId) {
      buttonRef.current?.click();
    }
  };

  const onSubmitCustom = (e: React.FormEvent) => {
    e.preventDefault();
    const url = `${BASE_URL}/${nextStep.id}`;
    onSubmit();
    history.push(url);
  };

  return (
    <ReportPageContainer isLoading={false} editMode={existingReport} className={styles.page}>
      <ReportFormPrompt confirmRedirect={confirmRedirect || isUpdated} onDiscard={clearReportState} report={report} />
      <form onSubmit={onSubmitCustom} className={styles.container}>
        <div className={styles.inner}>
          {hideSteps ? (
            <div className={styles.placeholder} />
          ) : (
            <Stepper activeStep={activeStep} onStepChange={onStepChange} />
          )}
          <div className={styles.content}>{children}</div>
        </div>
        {!editMode && (
          <div className={styles.buttonRow}>
            <div className={styles.buttonRowInner}>
              {previousStep && (
                <Button variant={'secondary'} onClick={() => goToPreviousStep(activeStep)}>
                  Previous: {previousStep.name}
                </Button>
              )}
              <Button ref={buttonRef} disabled={disabled}>
                {buttonText}
              </Button>
            </div>
          </div>
        )}
      </form>
    </ReportPageContainer>
  );
};

const getStyles = (theme: GrafanaTheme2) => {
  return {
    page: css`
      .page-container {
        max-width: none;
        padding: 0;
      }
    `,
    container: css`
      display: flex;
      flex-direction: column;
      height: 100%;
    `,
    content: css`
      width: min(70%, 800px);
      padding-bottom: ${theme.spacing(3)};
    `,
    placeholder: css`
      width: min(30%, 272px);
    `,
    inner: css`
      display: flex;
      justify-content: flex-start;
      flex: 1 0 auto;
      padding: ${theme.spacing(0, 7)};
    `,
    buttonRow: css`
      display: flex;
      padding: ${theme.spacing(2, 0)};
      border-top: 1px solid ${theme.colors.secondary.border};
      width: 100%;
      position: sticky;
      bottom: 0;
      z-index: 9;
      background-color: ${theme.colors.background.primary};

      button:first-of-type {
        margin-right: ${theme.spacing(2)};
      }
    `,
    buttonRowInner: css`
      display: flex;
      justify-content: flex-start;
      margin-left: calc(min(30%, 200px) + 128px); // align with form
      width: min(70%, 800px);
    `,
  };
};

export default connector(ReportForm);
