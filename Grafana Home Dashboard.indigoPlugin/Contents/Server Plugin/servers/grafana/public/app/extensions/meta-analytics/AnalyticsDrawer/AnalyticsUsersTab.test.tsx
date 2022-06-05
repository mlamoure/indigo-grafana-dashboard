import { render, screen, within } from '@testing-library/react';
import $ from 'jquery';
import React from 'react';

import { createTheme } from '@grafana/data';
import { DashboardModel } from 'app/features/dashboard/state';

import { getMockDailySummaries } from '../__mocks__/dailySummariesMocks';
import { getMockRecentUsers } from '../__mocks__/recentUsersMocks';
import { getDashboardUsersInfo, DashboardDailySummaryDTO, UserViewDTO } from '../api';

import { AnalyticsUsersTab, Props } from './AnalyticsUsersTab';

beforeEach(() => {
  jest.clearAllMocks();
});

jest.mock(
  'react-virtualized-auto-sizer',
  () =>
    ({ children }: any) =>
      children({ height: 600, width: 600 })
);
jest.mock('../api', () => {
  return {
    getDashboardUsersInfo: jest.fn((dashboardId: number) => {
      const recentUsers = getMockRecentUsers();
      return Promise.resolve({
        creator: dashboardId ? recentUsers[0] : null,
        lastEditor: dashboardId ? recentUsers[1] : null,
      });
    }),
  };
});
//@ts-ignore
$.plot = jest.fn();

const setup = (dashboard: DashboardModel, dailySummaries: DashboardDailySummaryDTO[], userViews: UserViewDTO[]) => {
  const props: Props = {
    dashboard,
    dailySummaries,
    userViews,
    theme: createTheme(),
    setDrawerOpen: jest.fn() as any,
  };
  render(<AnalyticsUsersTab {...props} />);
};

describe('Render', () => {
  it('should render empty component - no data', async () => {
    setup(new DashboardModel({ id: 0 }), [], []);
    expect(screen.queryByLabelText('User information box')).not.toBeInTheDocument();
    expect(screen.queryByRole('main')).not.toBeInTheDocument();
  });

  it('should render dashboard meta information', async () => {
    setup(new DashboardModel({ id: 1 }), [], []);
    expect(getDashboardUsersInfo).toHaveBeenCalledTimes(1);

    expect(await screen.findAllByLabelText('User information box')).toHaveLength(2);
    expect(screen.queryByRole('main')).not.toBeInTheDocument();
  });

  it('should render views from daily summaries', async () => {
    setup(new DashboardModel({ id: 0 }), getMockDailySummaries(), []);

    expect(await screen.findByRole('main')).toBeInTheDocument();
    expect(screen.queryByLabelText('User information box')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Graph container')).toBeInTheDocument();
  });

  it('should render recent users information', async () => {
    const userViews = getMockRecentUsers();
    setup(new DashboardModel({ id: 0 }, { showSettings: true }), [], userViews);

    expect(await screen.findByRole('main')).toBeInTheDocument();
    expect(screen.getAllByLabelText('User information box')).toHaveLength(1);
    expect(screen.getByLabelText('User box title')).toHaveTextContent('Last viewed');
    expect(screen.getByLabelText('Version history button')).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(userViews.length + 1);
    expect(screen.getAllByRole('cell')).toHaveLength(3 * userViews.length);

    const { queryAllByLabelText } = within(screen.getByRole('table'));
    expect(queryAllByLabelText('Avatar icon').concat(queryAllByLabelText('Initials icon'))).toHaveLength(
      userViews.length
    );
  });

  it('should not render version history button', async () => {
    const userViews = getMockRecentUsers();
    setup(new DashboardModel({ id: 0 }, { canSave: false }), [], userViews);

    expect(await screen.findByRole('main')).toBeInTheDocument();
    expect(screen.queryByLabelText('Version history button')).not.toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(userViews.length + 1);
  });
});
