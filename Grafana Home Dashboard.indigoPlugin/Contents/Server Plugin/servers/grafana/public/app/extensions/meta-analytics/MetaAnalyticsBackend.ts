import { EchoBackend, EchoEvent, EchoEventType, getBackendSrv, MetaAnalyticsEvent } from '@grafana/runtime';

export interface MetaAnalyticsBackendOptions {
  url: string;
}

export class MetaAnalyticsBackend implements EchoBackend<MetaAnalyticsEvent, MetaAnalyticsBackendOptions> {
  private buffer: MetaAnalyticsEvent[] = [];
  supportedEvents = [EchoEventType.MetaAnalytics];

  constructor(public options: MetaAnalyticsBackendOptions) {}

  addEvent = (e: EchoEvent) => {
    this.buffer.push(e);
  };

  flush = () => {
    if (this.buffer.length === 0) {
      return;
    }

    const result: any[] = [];
    for (const event of this.buffer) {
      result.push({
        type: event.type,
        ...event.payload,
        meta: event.meta,
      });
    }

    // Currently we don have API for sending the metrics hence loging to console in dev environment
    if (process.env.NODE_ENV === 'development') {
      console.log('MetaAnalyticsBackend flushing:', result);
    }

    this.buffer = [];

    if (this.options.url) {
      getBackendSrv()
        .fetch({
          method: 'POST',
          url: this.options.url,
          showSuccessAlert: false,
          showErrorAlert: false,
          data: result,
        })
        .toPromise();
    }
  };
}
