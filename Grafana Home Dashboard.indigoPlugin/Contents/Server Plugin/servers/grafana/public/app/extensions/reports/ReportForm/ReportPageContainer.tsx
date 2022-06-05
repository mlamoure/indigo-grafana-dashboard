import { css, cx } from '@emotion/css';
import React, { HTMLAttributes, useEffect } from 'react';

import { GrafanaTheme2 } from '@grafana/data';
import { config } from '@grafana/runtime';
import { CustomScrollbar, IconButton, useStyles2 } from '@grafana/ui';
import PageLoader from 'app/core/components/PageLoader/PageLoader';

import { NoRendererInfoBox } from '../RenderingWarnings';

interface Props extends HTMLAttributes<HTMLDivElement> {
  isLoading: boolean;
  editMode?: boolean;
  children?: React.ReactNode;
}

export const ReportPageContainer = ({ children, editMode, isLoading, className, ...rest }: Props) => {
  const styles = useStyles2(getStyles);

  useEffect(() => {
    document.title = `Reporting: ${editMode ? 'Edit report' : 'New report'}`;
  }, [editMode]);

  return (
    <div className={cx(styles.page, className)} {...rest}>
      <CustomScrollbar autoHeightMin={'100%'}>
        <div className={styles.pageHeader}>
          <a href={'/reports'}>
            <IconButton name="arrow-left" size="xxl" />
          </a>
          <span>{`Reports / ${editMode ? 'Edit report' : 'New report'}`}</span>
        </div>
        <div className={'page-container'}>
          {isLoading ? <PageLoader /> : !config.rendererAvailable ? <NoRendererInfoBox variant="error" /> : children}
        </div>
      </CustomScrollbar>
    </div>
  );
};

const getStyles = (theme: GrafanaTheme2) => {
  return {
    header: css`
      font-size: ${theme.typography.h2.fontSize};
    `,
    page: css`
      height: 100%;
      overflow: auto;
      background: ${theme.components.panel.background};
      border: 1px solid ${theme.components.panel.borderColor};
    `,
    pageHeader: css`
      display: flex;
      align-items: center;
      font-size: ${theme.typography.h4.fontSize};
      padding: ${theme.spacing(3)};
      margin-bottom: ${theme.spacing(2)};

      a {
        display: flex;
        align-items: center;
        margin-right: ${theme.spacing(1)};
      }
    `,
  };
};
