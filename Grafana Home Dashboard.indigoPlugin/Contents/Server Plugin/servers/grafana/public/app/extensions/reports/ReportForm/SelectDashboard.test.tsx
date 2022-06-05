import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { Provider } from 'react-redux';
import { Router } from 'react-router-dom';

import { locationService } from '@grafana/runtime';
import { getRouteComponentProps } from 'app/core/navigation/__mocks__/routeProps';
import { addRootReducer, configureStore } from 'app/store/configureStore';

import { mockToolkitActionCreator } from '../../../../test/core/redux/mocks';
import reportsReducers, { initialState, updateReportProp } from '../state/reducers';

import { SelectDashboard, Props } from './SelectDashboard';

beforeEach(() => {
  jest.clearAllMocks();
});

jest.mock('app/core/services/backend_srv', () => {
  return {
    backendSrv: {
      search: async () => Promise.resolve([{ id: 1, uid: 'test', value: 1, title: 'test db' }]),
    },
  };
});

jest.mock('@grafana/runtime/src/config', () => ({
  config: {
    buildInfo: {},
    licenseInfo: {
      enabledFeatures: { 'reports.email': true },
    },
    featureToggles: {
      accesscontrol: true,
    },
    bootData: { navTree: [], user: {} },
    rendererAvailable: true,
  },
}));

jest.mock('app/core/core', () => {
  return {
    contextSrv: {
      hasPermission: () => true,
    },
  };
});

const blankReport = initialState.report;
const testReport = {
  ...blankReport,
  id: 1,
  name: 'Test report',
  dashboardId: 1,
  dashboardName: 'Test dashboard',
  recipients: 'test@me.com',
};

const setup = (propOverrides?: Partial<Props>) => {
  addRootReducer(reportsReducers);
  const store = configureStore();
  const props: Props = {
    ...getRouteComponentProps(),
    report: blankReport,
    variables: [],
    updateReportProp: mockToolkitActionCreator(updateReportProp),
    initVariables: jest.fn(),
    cleanUpVariables: jest.fn(),
    lastUid: '',
    ...propOverrides,
  };

  return render(
    <Provider store={store}>
      <Router history={locationService.getHistory()}>
        <SelectDashboard {...props} />
      </Router>
    </Provider>
  );
};

describe('SelectDashboard', () => {
  it('should render', () => {
    setup();
    expect(screen.getByText('1. Select dashboard')).toBeInTheDocument();
  });

  it('should not update the form if nothing was entered', async () => {
    const mockUpdate = jest.fn() as any;
    setup({ updateReportProp: mockUpdate });

    fireEvent.submit(screen.getByText(/next/i));

    await waitFor(() => expect(mockUpdate).not.toBeCalled());
  });

  it('should show the available data', () => {
    setup({ report: testReport });

    expect(screen.getByText('Test dashboard')).toBeInTheDocument();
    expect(screen.getByText('Select time range')).toBeInTheDocument();
  });

  it('should apply params from URL', async () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '&from=now-6h&to=now&db-uid=msRNFn-nz&db-id=1&db-name=Test%20dashboard',
      },
    });

    setup();

    expect(screen.getByText('Test dashboard')).toBeInTheDocument();
    expect(await screen.findByText('Last 6 hours')).toBeInTheDocument();
  });
});
