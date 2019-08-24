import {
  DEFAULT_RANGE,
  serializeStateToUrlParam,
  parseUrlState,
  updateHistory,
  clearHistory,
  hasNonEmptyQuery,
  instanceOfDataQueryError,
  getValueWithRefId,
  getFirstQueryErrorWithoutRefId,
  getRefIds,
} from './explore';
import { ExploreUrlState, ExploreMode } from 'app/types/explore';
import store from 'app/core/store';
import { LogsDedupStrategy } from '@grafana/data';
import { DataQueryError } from '@grafana/ui';

const DEFAULT_EXPLORE_STATE: ExploreUrlState = {
  datasource: null,
  queries: [],
  range: DEFAULT_RANGE,
  mode: ExploreMode.Metrics,
  ui: {
    showingGraph: true,
    showingTable: true,
    showingLogs: true,
    dedupStrategy: LogsDedupStrategy.none,
  },
};

describe('state functions', () => {
  describe('parseUrlState', () => {
    it('returns default state on empty string', () => {
      expect(parseUrlState('')).toMatchObject({
        datasource: null,
        queries: [],
        range: DEFAULT_RANGE,
      });
    });

    it('returns a valid Explore state from URL parameter', () => {
      const paramValue =
        '%7B"datasource":"Local","queries":%5B%7B"expr":"metric"%7D%5D,"range":%7B"from":"now-1h","to":"now"%7D%7D';
      expect(parseUrlState(paramValue)).toMatchObject({
        datasource: 'Local',
        queries: [{ expr: 'metric' }],
        range: {
          from: 'now-1h',
          to: 'now',
        },
      });
    });

    it('returns a valid Explore state from a compact URL parameter', () => {
      const paramValue = '%5B"now-1h","now","Local","5m",%7B"expr":"metric"%7D,"ui"%5D';
      expect(parseUrlState(paramValue)).toMatchObject({
        datasource: 'Local',
        queries: [{ expr: 'metric' }],
        range: {
          from: 'now-1h',
          to: 'now',
        },
      });
    });
  });

  describe('serializeStateToUrlParam', () => {
    it('returns url parameter value for a state object', () => {
      const state = {
        ...DEFAULT_EXPLORE_STATE,
        datasource: 'foo',
        queries: [
          {
            expr: 'metric{test="a/b"}',
          },
          {
            expr: 'super{foo="x/z"}',
          },
        ],
        range: {
          from: 'now-5h',
          to: 'now',
        },
      };

      expect(serializeStateToUrlParam(state)).toBe(
        '{"datasource":"foo","queries":[{"expr":"metric{test=\\"a/b\\"}"},' +
          '{"expr":"super{foo=\\"x/z\\"}"}],"range":{"from":"now-5h","to":"now"},' +
          '"mode":"Metrics",' +
          '"ui":{"showingGraph":true,"showingTable":true,"showingLogs":true,"dedupStrategy":"none"}}'
      );
    });

    it('returns url parameter value for a state object', () => {
      const state = {
        ...DEFAULT_EXPLORE_STATE,
        datasource: 'foo',
        queries: [
          {
            expr: 'metric{test="a/b"}',
          },
          {
            expr: 'super{foo="x/z"}',
          },
        ],
        range: {
          from: 'now-5h',
          to: 'now',
        },
      };
      expect(serializeStateToUrlParam(state, true)).toBe(
        '["now-5h","now","foo",{"expr":"metric{test=\\"a/b\\"}"},{"expr":"super{foo=\\"x/z\\"}"},{"mode":"Metrics"},{"ui":[true,true,true,"none"]}]'
      );
    });
  });

  describe('interplay', () => {
    it('can parse the serialized state into the original state', () => {
      const state = {
        ...DEFAULT_EXPLORE_STATE,
        datasource: 'foo',
        queries: [
          {
            expr: 'metric{test="a/b"}',
          },
          {
            expr: 'super{foo="x/z"}',
          },
        ],
        range: {
          from: 'now - 5h',
          to: 'now',
        },
      };
      const serialized = serializeStateToUrlParam(state);
      const parsed = parseUrlState(serialized);
      expect(state).toMatchObject(parsed);
    });

    it('can parse the compact serialized state into the original state', () => {
      const state = {
        ...DEFAULT_EXPLORE_STATE,
        datasource: 'foo',
        queries: [
          {
            expr: 'metric{test="a/b"}',
          },
          {
            expr: 'super{foo="x/z"}',
          },
        ],
        range: {
          from: 'now - 5h',
          to: 'now',
        },
      };
      const serialized = serializeStateToUrlParam(state, true);
      const parsed = parseUrlState(serialized);
      expect(state).toMatchObject(parsed);
    });
  });
});

describe('updateHistory()', () => {
  const datasourceId = 'myDatasource';
  const key = `grafana.explore.history.${datasourceId}`;

  beforeEach(() => {
    clearHistory(datasourceId);
    expect(store.exists(key)).toBeFalsy();
  });

  test('should save history item to localStorage', () => {
    const expected = [
      {
        query: { refId: '1', expr: 'metric' },
      },
    ];
    expect(updateHistory([], datasourceId, [{ refId: '1', expr: 'metric' }])).toMatchObject(expected);
    expect(store.exists(key)).toBeTruthy();
    expect(store.getObject(key)).toMatchObject(expected);
  });
});

describe('hasNonEmptyQuery', () => {
  test('should return true if one query is non-empty', () => {
    expect(hasNonEmptyQuery([{ refId: '1', key: '2', context: 'explore', expr: 'foo' }])).toBeTruthy();
  });

  test('should return false if query is empty', () => {
    expect(hasNonEmptyQuery([{ refId: '1', key: '2', context: 'panel' }])).toBeFalsy();
  });

  test('should return false if no queries exist', () => {
    expect(hasNonEmptyQuery([])).toBeFalsy();
  });
});

describe('instanceOfDataQueryError', () => {
  describe('when called with a DataQueryError', () => {
    it('then it should return true', () => {
      const error: DataQueryError = {
        message: 'A message',
        status: '200',
        statusText: 'Ok',
      };
      const result = instanceOfDataQueryError(error);

      expect(result).toBe(true);
    });
  });

  describe('when called with a non DataQueryError', () => {
    it('then it should return false', () => {
      const error = {};
      const result = instanceOfDataQueryError(error);

      expect(result).toBe(false);
    });
  });
});

describe('hasRefId', () => {
  describe('when called with a null value', () => {
    it('then it should return null', () => {
      const input = null;
      const result = getValueWithRefId(input);

      expect(result).toBeNull();
    });
  });

  describe('when called with a non object value', () => {
    it('then it should return null', () => {
      const input = 123;
      const result = getValueWithRefId(input);

      expect(result).toBeNull();
    });
  });

  describe('when called with an object that has refId', () => {
    it('then it should return the object', () => {
      const input = { refId: 'A' };
      const result = getValueWithRefId(input);

      expect(result).toBe(input);
    });
  });

  describe('when called with an array that has refId', () => {
    it('then it should return the object', () => {
      const input = [123, null, {}, { refId: 'A' }];
      const result = getValueWithRefId(input);

      expect(result).toBe(input[3]);
    });
  });

  describe('when called with an object that has refId somewhere in the object tree', () => {
    it('then it should return the object', () => {
      const input: any = { data: [123, null, {}, { series: [123, null, {}, { refId: 'A' }] }] };
      const result = getValueWithRefId(input);

      expect(result).toBe(input.data[3].series[3]);
    });
  });
});

describe('getFirstQueryErrorWithoutRefId', () => {
  describe('when called with a null value', () => {
    it('then it should return null', () => {
      const errors: DataQueryError[] = null;
      const result = getFirstQueryErrorWithoutRefId(errors);

      expect(result).toBeNull();
    });
  });

  describe('when called with an array with only refIds', () => {
    it('then it should return undefined', () => {
      const errors: DataQueryError[] = [{ refId: 'A' }, { refId: 'B' }];
      const result = getFirstQueryErrorWithoutRefId(errors);

      expect(result).toBeUndefined();
    });
  });

  describe('when called with an array with and without refIds', () => {
    it('then it should return undefined', () => {
      const errors: DataQueryError[] = [
        { refId: 'A' },
        { message: 'A message' },
        { refId: 'B' },
        { message: 'B message' },
      ];
      const result = getFirstQueryErrorWithoutRefId(errors);

      expect(result).toBe(errors[1]);
    });
  });
});

describe('getRefIds', () => {
  describe('when called with a null value', () => {
    it('then it should return empty array', () => {
      const input = null;
      const result = getRefIds(input);

      expect(result).toEqual([]);
    });
  });

  describe('when called with a non object value', () => {
    it('then it should return empty array', () => {
      const input = 123;
      const result = getRefIds(input);

      expect(result).toEqual([]);
    });
  });

  describe('when called with an object that has refId', () => {
    it('then it should return an array with that refId', () => {
      const input = { refId: 'A' };
      const result = getRefIds(input);

      expect(result).toEqual(['A']);
    });
  });

  describe('when called with an array that has refIds', () => {
    it('then it should return an array with unique refIds', () => {
      const input = [123, null, {}, { refId: 'A' }, { refId: 'A' }, { refId: 'B' }];
      const result = getRefIds(input);

      expect(result).toEqual(['A', 'B']);
    });
  });

  describe('when called with an object that has refIds somewhere in the object tree', () => {
    it('then it should return return an array with unique refIds', () => {
      const input: any = {
        data: [
          123,
          null,
          { refId: 'B', series: [{ refId: 'X' }] },
          { refId: 'B' },
          {},
          { series: [123, null, {}, { refId: 'A' }] },
        ],
      };
      const result = getRefIds(input);

      expect(result).toEqual(['B', 'X', 'A']);
    });
  });
});
