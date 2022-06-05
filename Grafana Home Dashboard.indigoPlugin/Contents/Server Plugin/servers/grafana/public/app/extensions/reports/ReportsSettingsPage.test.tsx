import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import React from 'react';

import { NavModel } from '@grafana/data';

import { Props, ReportsSettingsPage } from './ReportsSettingsPage';

beforeEach(() => {
  jest.clearAllMocks();
});

const mockPost = jest.fn(() => {
  return Promise.resolve([]);
});

jest.mock('@grafana/runtime', () => {
  return {
    getBackendSrv() {
      return {
        get: (url: string) => {
          return {
            branding: {
              emailFooterLink: 'https://footer-link.com',
              emailFooterMode: 'sent-by',
              emailFooterText: 'Test',
              emailLogoUrl: 'https://email-logo.jpg',
              reportLogoUrl: 'https://report-logo.jpg',
            },
            id: 0,
            orgId: 1,
            userId: 1,
          };
        },
        post: mockPost,
      };
    },
    locationService: {
      push: jest.fn(),
    },
    config: {
      buildInfo: {},
      licenseInfo: {},
      rendererAvailable: true,
    },
  };
});

jest.mock('@grafana/runtime/src/config', () => ({
  config: {
    buildInfo: {},
    licenseInfo: {},
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

const setup = (propOverrides?: Partial<Props>) => {
  const props: Props = {
    navModel: { node: {}, main: {} } as NavModel,
  };

  Object.assign(props, propOverrides);

  render(<ReportsSettingsPage {...props} />);
};

describe('ReportsSettingPage', () => {
  it('should render existing settings', async () => {
    setup();

    expect(await screen.findAllByPlaceholderText('http://your.site/logo.png')).toHaveLength(2);
    expect(screen.getByLabelText(/report logo/i)).toHaveAttribute('value', 'https://report-logo.jpg');
    expect(screen.getByLabelText(/email logo/i)).toHaveAttribute('value', 'https://email-logo.jpg');
    expect(screen.getByRole('radio', { name: /sent by/i })).toBeChecked();
    expect(screen.getByRole('textbox', { name: /footer link text/i })).toHaveAttribute('value', 'Test');
    expect(screen.getByRole('textbox', { name: /footer link url/i })).toHaveAttribute(
      'value',
      'https://footer-link.com'
    );
  });

  it('should hide footer link and text if footer mode is None', async () => {
    setup();
    expect(await screen.findByRole('radio', { name: /sent by/i })).toBeChecked();
    expect(screen.getByRole('textbox', { name: /footer link text/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /footer link url/i })).toBeInTheDocument();

    const none = screen.getByRole('radio', { name: /none/i });
    fireEvent.click(none);

    expect(await screen.findByRole('radio', { name: /none/i })).toBeChecked();
    expect(screen.queryByRole('textbox', { name: /footer link text/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /footer link url/i })).not.toBeInTheDocument();
  });

  it('should update the form fields on change', async () => {
    setup();

    const reportLogo = await screen.findByLabelText(/report logo/i);
    fireEvent.input(reportLogo, { target: { value: 'http://new-logo.png' } });
    fireEvent.input(screen.getByRole('textbox', { name: /footer link text/i }), { target: { value: 'New company' } });

    fireEvent.submit(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        '/api/reports/settings',
        expect.objectContaining({
          branding: {
            emailFooterLink: 'https://footer-link.com',
            emailFooterMode: 'sent-by',
            emailFooterText: 'New company',
            emailLogoUrl: 'https://email-logo.jpg',
            reportLogoUrl: 'http://new-logo.png',
          },
        })
      );
    });
  });
});
