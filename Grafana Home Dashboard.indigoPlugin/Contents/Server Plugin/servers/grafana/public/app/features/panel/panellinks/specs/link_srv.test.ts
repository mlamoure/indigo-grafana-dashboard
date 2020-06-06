import { LinkSrv } from '../link_srv';
import { DataLinkBuiltInVars, locationUtil, VariableModel } from '@grafana/data';
import { TimeSrv } from 'app/features/dashboard/services/TimeSrv';
import { TemplateSrv } from 'app/features/templating/template_srv';
import { advanceTo } from 'jest-date-mock';
import { updateConfig } from '../../../../core/config';
import { variableAdapters } from '../../../variables/adapters';
import { createQueryVariableAdapter } from '../../../variables/query/adapter';

jest.mock('app/core/core', () => ({
  appEvents: {
    on: () => {},
  },
}));

const dataPointMock = {
  seriesName: 'A-series',
  datapoint: [1000000001, 1],
};

describe('linkSrv', () => {
  let linkSrv: LinkSrv;

  function initLinkSrv() {
    const rootScope = {
      $on: jest.fn(),
      onAppEvent: jest.fn(),
      appEvent: jest.fn(),
    };

    const timer = {
      register: jest.fn(),
      cancel: jest.fn(),
      cancelAll: jest.fn(),
    };

    const location = {
      search: jest.fn(() => ({})),
    };

    const _dashboard: any = {
      time: { from: 'now-6h', to: 'now' },
      getTimezone: jest.fn(() => 'browser'),
    };

    const timeSrv = new TimeSrv(rootScope as any, jest.fn() as any, location as any, timer, {} as any);
    timeSrv.init(_dashboard);
    timeSrv.setTime({ from: 'now-1h', to: 'now' });
    _dashboard.refresh = false;

    const variablesMock = [
      {
        type: 'query',
        name: 'test1',
        label: 'Test1',
        hide: false,
        current: { value: 'val1' },
        skipUrlSync: false,
        getValueForUrl: function() {
          return 'val1';
        },
      } as VariableModel,
      {
        type: 'query',
        name: 'test2',
        label: 'Test2',
        hide: false,
        current: { value: 'val2' },
        skipUrlSync: false,
        getValueForUrl: function() {
          return 'val2';
        },
      } as VariableModel,
    ];
    const _templateSrv = new TemplateSrv({
      // @ts-ignore
      getVariables: () => {
        return variablesMock;
      },
      // @ts-ignore
      getVariableWithName: (name: string) => {
        return variablesMock.filter(v => v.name === name)[0];
      },
    });

    linkSrv = new LinkSrv(_templateSrv, timeSrv);
  }

  beforeAll(() => {
    variableAdapters.register(createQueryVariableAdapter());
  });

  beforeEach(() => {
    initLinkSrv();
    advanceTo(1000000000);
  });

  describe('built in variables', () => {
    it('should add time range to url if $__url_time_range variable present', () => {
      expect(
        linkSrv.getDataLinkUIModel(
          {
            title: 'Any title',
            url: `/d/1?$${DataLinkBuiltInVars.keepTime}`,
          },
          {},
          {}
        ).href
      ).toEqual('/d/1?from=now-1h&to=now');
    });

    it('should add all variables to url if $__all_variables variable present', () => {
      expect(
        linkSrv.getDataLinkUIModel(
          {
            title: 'Any title',
            url: `/d/1?$${DataLinkBuiltInVars.includeVars}`,
          },
          {},
          {}
        ).href
      ).toEqual('/d/1?var-test1=val1&var-test2=val2');
    });

    it('should interpolate series name', () => {
      expect(
        linkSrv.getDataLinkUIModel(
          {
            title: 'Any title',
            url: `/d/1?var-test=$\{${DataLinkBuiltInVars.seriesName}}`,
          },
          {
            __series: {
              value: {
                name: 'A-series',
              },
              text: 'A-series',
            },
          },
          {}
        ).href
      ).toEqual('/d/1?var-test=A-series');
    });
    it('should interpolate value time', () => {
      expect(
        linkSrv.getDataLinkUIModel(
          {
            title: 'Any title',
            url: `/d/1?time=$\{${DataLinkBuiltInVars.valueTime}}`,
          },
          {
            __value: {
              value: { time: dataPointMock.datapoint[0] },
              text: 'Value',
            },
          },
          {}
        ).href
      ).toEqual('/d/1?time=1000000001');
    });
    it('should not trim white space from data links', () => {
      expect(
        linkSrv.getDataLinkUIModel(
          {
            title: 'White space',
            url: 'www.google.com?query=some query',
          },
          {
            __value: {
              value: { time: dataPointMock.datapoint[0] },
              text: 'Value',
            },
          },
          {}
        ).href
      ).toEqual('www.google.com?query=some query');
    });
    it('should remove new lines from data link', () => {
      expect(
        linkSrv.getDataLinkUIModel(
          {
            title: 'New line',
            url: 'www.google.com?query=some\nquery',
          },
          {
            __value: {
              value: { time: dataPointMock.datapoint[0] },
              text: 'Value',
            },
          },
          {}
        ).href
      ).toEqual('www.google.com?query=somequery');
    });
  });

  describe('sanitization', () => {
    const url = "javascript:alert('broken!);";
    it.each`
      disableSanitizeHtml | expected
      ${true}             | ${url}
      ${false}            | ${'about:blank'}
    `(
      "when disable disableSanitizeHtml set to '$disableSanitizeHtml' then result should be '$expected'",
      ({ disableSanitizeHtml, expected }) => {
        updateConfig({
          disableSanitizeHtml,
        });

        const link = linkSrv.getDataLinkUIModel(
          {
            title: 'Any title',
            url,
          },
          {
            __value: {
              value: { time: dataPointMock.datapoint[0] },
              text: 'Value',
            },
          },
          {}
        ).href;

        expect(link).toBe(expected);
      }
    );
  });

  describe('Building links with root_url set', () => {
    it.each`
      url                 | appSubUrl     | expected
      ${'/d/XXX'}         | ${'/grafana'} | ${'/grafana/d/XXX'}
      ${'/grafana/d/XXX'} | ${'/grafana'} | ${'/grafana/d/XXX'}
      ${'d/whatever'}     | ${'/grafana'} | ${'d/whatever'}
      ${'/d/XXX'}         | ${''}         | ${'/d/XXX'}
      ${'/grafana/d/XXX'} | ${''}         | ${'/grafana/d/XXX'}
      ${'d/whatever'}     | ${''}         | ${'d/whatever'}
    `(
      "when link '$url' and config.appSubUrl set to '$appSubUrl' then result should be '$expected'",
      ({ url, appSubUrl, expected }) => {
        locationUtil.initialize({
          getConfig: () => {
            return { appSubUrl } as any;
          },
          // @ts-ignore
          buildParamsFromVariables: () => {},
          // @ts-ignore
          getTimeRangeForUrl: () => {},
        });

        const link = linkSrv.getDataLinkUIModel(
          {
            title: 'Any title',
            url,
          },
          {
            __value: {
              value: { time: dataPointMock.datapoint[0] },
              text: 'Value',
            },
          },
          {}
        ).href;

        expect(link).toBe(expected);
      }
    );
  });
});
