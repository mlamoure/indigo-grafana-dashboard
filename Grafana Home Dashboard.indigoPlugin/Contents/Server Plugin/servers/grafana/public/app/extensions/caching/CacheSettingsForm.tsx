import React from 'react';

import { Field, Switch, Input, Button, HorizontalGroup, Tooltip, Icon, Label } from '@grafana/ui';

import { CacheSettingsDisable } from './CacheSettingsDisable';
import { Props } from './DataSourceCache';

interface CacheSettingsProps {
  loading: boolean;
  setUseDefaultTTL: (useDefaultTTL: boolean) => void;
  setTtlQueriesMs: (ttl: number) => void;
  setTtlResourcesMs: (ttl: number) => void;
}

export const CacheSettingsForm = (props: Props & CacheSettingsProps) => {
  const {
    updateDataSourceCache,
    pageId,
    useDefaultTTL,
    setUseDefaultTTL,
    defaultTTLMs,
    ttlQueriesMs,
    setTtlQueriesMs,
    ttlResourcesMs,
    setTtlResourcesMs,
    loading,
    enabled,
    dataSourceID,
    dataSourceUID,
  } = props;

  return (
    <div>
      <Field
        description="Enable this to use the default TTL set in Grafana's configuration"
        label="Use Default TTL"
        disabled={loading}
      >
        <Switch
          value={useDefaultTTL}
          onChange={() => {
            setUseDefaultTTL(!useDefaultTTL);
          }}
        />
      </Field>
      <Field
        description="The time-to-live for a query cache item in milliseconds. Example: 5000"
        label="Query TTL"
        disabled={loading || useDefaultTTL}
      >
        <Input
          type="number"
          className="max-width-10"
          placeholder="1000"
          min={0}
          value={(useDefaultTTL ? defaultTTLMs : ttlQueriesMs) || 0}
          onChange={(el) => {
            setTtlQueriesMs(el.currentTarget.valueAsNumber);
          }}
        />
      </Field>
      <Field
        description="The time-to-live for resources cache items in milliseconds. Example: 5000"
        label={
          <Label>
            <span>Resource TTL</span>
            <Tooltip
              content={
                <div>
                  Resources are dynamic values that Grafana data source plugins retrieve from data sources for use in
                  the query editor. Examples are Splunk namespaces, Prometheus labels, and CloudWatch metric names.
                  Since these values update less frequently, you might prefer a longer cache TTL for Resources than
                  queries. See the <a href="https://grafana.com/docs/grafana/latest/enterprise/query-caching/">docs</a>{' '}
                  for more info.
                </div>
              }
            >
              <Icon name="question-circle" />
            </Tooltip>
          </Label>
        }
        disabled={loading || useDefaultTTL}
      >
        <Input
          type="number"
          className="max-width-10"
          placeholder="1000"
          min={0}
          value={(useDefaultTTL ? defaultTTLMs : ttlResourcesMs) || 0}
          onChange={(el) => {
            setTtlResourcesMs(el.currentTarget.valueAsNumber);
          }}
        />
      </Field>
      <HorizontalGroup spacing="md" align="flex-start" justify="flex-start">
        <CacheSettingsDisable {...props} />
        <Button
          disabled={loading}
          onClick={() =>
            updateDataSourceCache(pageId, {
              dataSourceID,
              dataSourceUID,
              enabled,
              defaultTTLMs,
              ttlQueriesMs,
              ttlResourcesMs,
              useDefaultTTL,
            })
          }
        >
          Save
        </Button>
      </HorizontalGroup>
    </div>
  );
};
