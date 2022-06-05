import { css, cx } from '@emotion/css';
import React from 'react';
import { ConnectedProps, connect } from 'react-redux';

import { GrafanaTheme2 } from '@grafana/data';
import { Link, useStyles2, Icon } from '@grafana/ui';

import { EnterpriseStoreState, StepKey } from '../../types';
import { BASE_URL, requiredFields } from '../constants';
import { reportSteps } from '../index';

const mapStateToProps = (state: EnterpriseStoreState) => {
  const { report, visitedSteps } = state.reports;
  return {
    report,
    visitedSteps,
  };
};

export interface OwnProps {
  activeStep?: StepKey;
  onStepChange: () => void;
}

const connector = connect(mapStateToProps, {});
export type Props = ConnectedProps<typeof connector> & OwnProps;

export const Stepper = ({ report, onStepChange, visitedSteps, activeStep = StepKey.SelectDashboard }: Props) => {
  const styles = useStyles2(getStyles);
  const lastStep = reportSteps[reportSteps.length - 1];

  return (
    <ol className={styles.container}>
      {reportSteps.map((step) => {
        const isLast = step.id === lastStep.id;
        const isActive = step.id === activeStep;
        const isVisited = visitedSteps.includes(step.id) || activeStep === lastStep.id;
        const requiredSectionFields = requiredFields.find((field) => field.step === step.id)?.fields;
        const hasMissingFields = requiredSectionFields?.some((field) => !report[field]);
        const successField = !isActive && !isLast && isVisited && !hasMissingFields;
        const warnField = !isActive && !isLast && isVisited && hasMissingFields;
        const itemStyles = cx(styles.item, {
          [styles.active]: isActive,
          [styles.successItem]: successField,
          [styles.warnItem]: warnField,
        });

        return (
          <li key={step.id} className={itemStyles}>
            {successField && <Icon name={'check'} size={'xl'} className={styles.successItem} />}
            {warnField && <Icon name={'exclamation-triangle'} className={styles.warnItem} />}
            <Link
              onClick={!isActive ? onStepChange : undefined}
              href={`${BASE_URL}/${step.id}`}
              className={styles.link}
            >
              {step.name}
            </Link>
            {!isLast && <div className={styles.divider} />}
          </li>
        );
      })}
    </ol>
  );
};

const getStyles = (theme: GrafanaTheme2) => {
  return {
    container: css`
      counter-reset: item;
      list-style-type: none;
      width: min(30%, 200px);
      margin-right: ${theme.spacing(9)};
      position: relative;

      &::after {
        content: '';
        background-color: ${theme.colors.border.medium};
        position: absolute;
        top: 0;
        right: 0;
        height: 240px;
        width: 1px;
      }
    `,
    item: css`
      color: ${theme.colors.text.secondary};
    `,
    successItem: css`
      a {
        &::before {
          content: '';
        }
      }

      svg {
        color: ${theme.colors.success.text};
        margin: ${theme.spacing(0, 0.5, 0, -1)};
      }
    `,
    warnItem: css`
      a::before {
        content: '';
      }
      svg {
        color: ${theme.colors.warning.text};
        margin: ${theme.spacing(0, 1, 0.5, -0.5)};
      }
    `,
    link: css`
      color: inherit;
      &:hover {
        color: ${theme.colors.text.link};
      }

      &::before {
        content: counter(item) '  ';
        counter-increment: item;
      }
    `,
    active: css`
      font-weight: 500;
      color: ${theme.colors.text.maxContrast};

      &::before {
        font-weight: 500;
      }
    `,
    divider: css`
      height: ${theme.spacing(2)};
      border-left: 1px dotted ${theme.colors.text.secondary};
      margin: ${theme.spacing(1, 0.5)};
    `,
  };
};

export default connector(Stepper);
