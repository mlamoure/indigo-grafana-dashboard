import { css, cx } from '@emotion/css';
import { isEqual } from 'lodash';
import React, { FC, useState, useEffect } from 'react';
import { connect, ConnectedProps } from 'react-redux';

import { GrafanaTheme } from '@grafana/data';
import { Button, stylesFactory, useTheme } from '@grafana/ui';
import { contextSrv } from 'app/core/services/context_srv';
import { addCustomLeftAction } from 'app/features/dashboard/components/DashNav/DashNav';
import { DashboardModel } from 'app/features/dashboard/state';

import { AnalyticsTab } from '../types';

import { UserIcon, getUserIconStyles } from './UserIcon';
import { getRecentUsers, UserViewDTO } from './api';
import { openDrawer } from './state/actions';

const getPresenceIndicatorsStyles = stylesFactory((theme: GrafanaTheme, tooManyUsers: boolean) => {
  return {
    container: css`
      display: flex;
      justify-content: center;
      flex-direction: row-reverse;
      margin-left: ${theme.spacing.sm};
    `,
    moreIcon: css`
      cursor: pointer;
      span {
        margin-bottom: ${tooManyUsers ? '3px' : '0px'};
      }
    `,
  };
});

export interface Props {
  dashboard?: DashboardModel;
}

const mapDispatchToProps = {
  openDrawer,
};

const connector = connect(null, mapDispatchToProps);
export type PresenceIndicatorsProps = ConnectedProps<typeof connector> & Props;

const iconLimit = 4;
const refreshInterval = 60000; // In milliseconds

function fetchRecentUsers(dashboardId: number, setRecentUsers: React.Dispatch<React.SetStateAction<UserViewDTO[]>>) {
  const user = contextSrv.user;
  getRecentUsers(dashboardId).then((data) => {
    const items = data.filter((item: UserViewDTO) => item.user.id !== user.id);
    setRecentUsers((recentUsers: UserViewDTO[]) => (isEqual(items, recentUsers) ? recentUsers : items));
  });
}

export const PresenceIndicators: FC<PresenceIndicatorsProps> = ({ dashboard, openDrawer }) => {
  const dashboardId = dashboard?.id;
  const [recentUsers, setRecentUsers] = useState<UserViewDTO[]>([]);

  const nbOfUsers = recentUsers.length - iconLimit + 1;
  const tooManyUsers = nbOfUsers > 9;

  const theme = useTheme();
  const mainStyles = getPresenceIndicatorsStyles(theme, tooManyUsers);
  const iconStyles = getUserIconStyles(theme, false, true);

  useEffect(() => {
    if (!dashboardId || !dashboard?.meta.url) {
      return undefined;
    }

    fetchRecentUsers(dashboardId, setRecentUsers);
    const interval = setInterval(() => fetchRecentUsers(dashboardId, setRecentUsers), refreshInterval);
    return () => {
      clearInterval(interval);
    };
  }, [dashboardId, dashboard]);

  const iconLimitReached = recentUsers.length > iconLimit;
  return (
    <>
      {recentUsers.length > 0 && (
        <div className={mainStyles.container} aria-label="Presence indicators container">
          {iconLimitReached && (
            <Button
              variant="secondary"
              className={cx(iconStyles.textIcon, iconStyles.icon, mainStyles.moreIcon)}
              aria-label="More users icon"
              onClick={() => openDrawer(AnalyticsTab.Users)}
            >
              {tooManyUsers ? '...' : `+${nbOfUsers}`}
            </Button>
          )}
          {recentUsers
            .slice(0, iconLimitReached ? iconLimit - 1 : iconLimit)
            .reverse()
            .map((userView) => (
              <UserIcon key={userView.user.id} userView={userView} showBorder={true} />
            ))}
        </div>
      )}
    </>
  );
};

export const initPresenceIndicators = () => {
  addCustomLeftAction({
    show: () => true,
    component: connector(PresenceIndicators),
    index: 'end',
  });
};
