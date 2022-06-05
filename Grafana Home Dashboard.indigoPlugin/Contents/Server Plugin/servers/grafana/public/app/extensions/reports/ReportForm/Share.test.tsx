import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { Provider } from 'react-redux';
import { Router } from 'react-router-dom';

import { locationService } from '@grafana/runtime';
import { getRouteComponentProps } from 'app/core/navigation/__mocks__/routeProps';
import { addRootReducer, configureStore } from 'app/store/configureStore';

import { mockToolkitActionCreator } from '../../../../test/core/redux/mocks';
import reportsReducers, { initialState, updateReportProp } from '../state/reducers';

import { Share, Props } from './Share';

beforeEach(() => {
  jest.clearAllMocks();
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
const mockUpdate = jest.fn() as any;

const setup = (propOverrides?: Partial<Props>) => {
  addRootReducer(reportsReducers);
  const store = configureStore();
  const props: Props = {
    ...getRouteComponentProps(),
    report: blankReport,
    testEmailIsSending: false,
    updateReportProp: mockToolkitActionCreator(updateReportProp),
    sendTestEmail: jest.fn(),
    ...propOverrides,
  };

  return render(
    <Provider store={store}>
      <Router history={locationService.getHistory()}>
        <Share {...props} />
      </Router>
    </Provider>
  );
};

describe('Share report', () => {
  it('should render', () => {
    setup();
    expect(screen.getByText(/4. Share/i)).toBeInTheDocument();
  });

  it('should save form values', async () => {
    setup({ updateReportProp: mockUpdate });
    userEvent.type(screen.getByRole('textbox', { name: /report name/i }), 'Test report');
    userEvent.type(screen.getByPlaceholderText(/Type in the recipients/), 'text@me.com');
    await userEvent.type(screen.getByPlaceholderText(/Type in the recipients/), '{enter}');
    userEvent.type(screen.getByRole('textbox', { name: /reply-to email/i }), 'reply@test.com');
    userEvent.click(screen.getByRole('checkbox', { name: /include a dashboard link/i }));
    fireEvent.submit(screen.getByRole('button', { name: /next/i }));

    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({
        ...blankReport,
        name: 'Test report',
        recipients: 'text@me.com',
        replyTo: 'reply@test.com',
        enableDashboardUrl: false,
      })
    );
  });

  it('should validate recipients', async () => {
    setup({ updateReportProp: mockUpdate });
    fireEvent.input(await screen.findByRole('textbox', { name: /report name/i }), { target: { value: 'Test report' } });
    await userEvent.type(screen.getByPlaceholderText(/Type in the recipients/), 'textme.com');
    await userEvent.type(screen.getByPlaceholderText(/Type in the recipients/), '{enter}');

    fireEvent.submit(screen.getByRole('button', { name: /next/i }));
    expect(await screen.findAllByRole('alert')).toHaveLength(1);
    expect((screen.getByRole('textbox', { name: /report name/i }) as HTMLInputElement).value).toBe('Test report');
  });

  it('should have "Send Test Email" button disabled until the required fields are provided', async () => {
    setup({ report: { ...blankReport, dashboardId: 1, dashboardName: 'Test dashboard' } });
    expect(screen.getByRole('button', { name: /send test email/i })).toBeDisabled();

    await userEvent.type(screen.getByRole('textbox', { name: /report name/i }), 'Test report');
    await userEvent.type(screen.getByPlaceholderText(/Type in the recipients/), 'test@example.com');
    await userEvent.type(screen.getByPlaceholderText(/Type in the recipients/), '{enter}');

    expect(screen.getByRole('button', { name: /send test email/i })).not.toBeDisabled();
  });
});
