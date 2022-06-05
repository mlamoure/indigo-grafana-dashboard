import { css } from '@emotion/css';
import React, { FC } from 'react';

import { GrafanaTheme } from '@grafana/data';
import { Alert, useStyles } from '@grafana/ui';

interface WarningProps {
  title: string;
  subTitle: JSX.Element;
  severity: 'info' | 'error';
  onButtonClick?: () => void;
  buttonText?: string;
}

const Warning: FC<WarningProps> = ({ title, subTitle, severity, onButtonClick, buttonText }) => {
  const styles = useStyles(getStyles);

  return (
    <div className={styles.container}>
      <div className="page-container">
        <Alert title={title} severity={severity} buttonContent={buttonText} onRemove={onButtonClick}>
          {subTitle}
        </Alert>
      </div>
    </div>
  );
};

interface LicensingLinkProps {
  isLicensingReader: boolean;
}

export const LicensingLink: FC<LicensingLinkProps> = ({ isLicensingReader, children }) => {
  if (isLicensingReader) {
    return <a href="/admin/licensing">{children}</a>;
  }

  return (
    <a
      href="https://grafana.com/docs/grafana/latest/enterprise/license-expiration/"
      target="_blank"
      rel="noreferrer noopener"
    >
      {children}
    </a>
  );
};

interface HasExpiredProps {
  isLicensingReader: boolean;
}

export const HasExpired: FC<HasExpiredProps> = ({ isLicensingReader }) => {
  return (
    <Warning
      title="Your Grafana Enterprise license has expired"
      subTitle={
        <>
          <LicensingLink isLicensingReader={isLicensingReader}>Some features</LicensingLink> have been disabled.
        </>
      }
      severity="error"
    />
  );
};

interface IsInvalidProps {
  isLicensingReader: boolean;
}

export const IsInvalid: FC<IsInvalidProps> = ({ isLicensingReader }) => {
  return (
    <Warning
      title="Your Grafana Enterprise license is invalid"
      subTitle={
        <>
          <LicensingLink isLicensingReader={isLicensingReader}>Some features</LicensingLink> have been disabled.
        </>
      }
      severity="error"
    />
  );
};

interface ExpiresSoonProps {
  days: number;
  onCloseWarning?(): void;
  isLicensingReader: boolean;
}

export const ExpiresSoon: FC<ExpiresSoonProps> = ({ days, onCloseWarning, isLicensingReader }) => {
  return (
    <Warning
      onButtonClick={onCloseWarning}
      title="Your Grafana Enterprise license will expire soon"
      subTitle={
        <>
          {days} days remaining, after which{' '}
          <LicensingLink isLicensingReader={isLicensingReader}>Enterprise features will be disabled.</LicensingLink>
        </>
      }
      severity="info"
      buttonText="Dismiss"
    />
  );
};

interface TokenExpiresSoonProps {
  days: number;
  onCloseWarning?(): void;
  isLicensingReader: boolean;
}

export const TokenExpiresSoon: FC<TokenExpiresSoonProps> = ({ days, onCloseWarning, isLicensingReader }) => {
  return (
    <Warning
      onButtonClick={onCloseWarning}
      title="Your Grafana Enterprise token needs to be renewed"
      subTitle={
        <>
          Your license token has {days} days remaining, after which{' '}
          <LicensingLink isLicensingReader={isLicensingReader}>Enterprise features will be disabled.</LicensingLink>
        </>
      }
      severity="info"
      buttonText="Dismiss"
    />
  );
};

interface MaxUsersReachedProps {
  activeUsers: number;
  maxUsers: number;
  type: string;
  onRefreshWarning?: () => void;
  slug?: string;
}

export const MaxUsersReached: FC<MaxUsersReachedProps> = ({ activeUsers, maxUsers, type, slug, onRefreshWarning }) => {
  return (
    <Warning
      onButtonClick={onRefreshWarning}
      title={'You have exceeded the included number of active ' + type}
      subTitle={
        <>
          Your Grafana Enterprise license includes {maxUsers} active {type}; you currently have {activeUsers} active{' '}
          {type}. Please{' '}
          {slug ? (
            <a href={'https://grafana.com/orgs/' + slug + '/licenses'} target="_blank" rel="noreferrer noopener">
              upgrade your license.
            </a>
          ) : (
            'upgrade your license.'
          )}
        </>
      }
      severity="error"
      buttonText="Refresh"
    />
  );
};

export const getStyles = (theme: GrafanaTheme) => {
  return {
    container: css`
      position: absolute;
      bottom: 0;
      width: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      z-index: 3;
    `,
  };
};
