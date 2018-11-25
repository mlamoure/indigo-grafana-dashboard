import React, { PureComponent } from 'react';

// TODO make this datasource-plugin-dependent
import QueryField from './PromQueryField';

class QueryRow extends PureComponent<any, {}> {
  onChangeQuery = (value, override?: boolean) => {
    const { index, onChangeQuery } = this.props;
    if (onChangeQuery) {
      onChangeQuery(value, index, override);
    }
  };

  onClickAddButton = () => {
    const { index, onAddQueryRow } = this.props;
    if (onAddQueryRow) {
      onAddQueryRow(index);
    }
  };

  onClickClearButton = () => {
    this.onChangeQuery('', true);
  };

  onClickHintFix = action => {
    const { index, onClickHintFix } = this.props;
    if (onClickHintFix) {
      onClickHintFix(action, index);
    }
  };

  onClickRemoveButton = () => {
    const { index, onRemoveQueryRow } = this.props;
    if (onRemoveQueryRow) {
      onRemoveQueryRow(index);
    }
  };

  onPressEnter = () => {
    const { onExecuteQuery } = this.props;
    if (onExecuteQuery) {
      onExecuteQuery();
    }
  };

  render() {
    const { edited, history, query, queryError, queryHint, request, supportsLogs } = this.props;
    return (
      <div className="query-row">
        <div className="query-row-field">
          <QueryField
            error={queryError}
            hint={queryHint}
            initialQuery={edited ? null : query}
            history={history}
            portalPrefix="explore"
            onClickHintFix={this.onClickHintFix}
            onPressEnter={this.onPressEnter}
            onQueryChange={this.onChangeQuery}
            request={request}
            supportsLogs={supportsLogs}
          />
        </div>
        <div className="query-row-tools">
          <button className="btn navbar-button navbar-button--tight" onClick={this.onClickClearButton}>
            <i className="fa fa-times" />
          </button>
          <button className="btn navbar-button navbar-button--tight" onClick={this.onClickAddButton}>
            <i className="fa fa-plus" />
          </button>
          <button className="btn navbar-button navbar-button--tight" onClick={this.onClickRemoveButton}>
            <i className="fa fa-minus" />
          </button>
        </div>
      </div>
    );
  }
}

export default class QueryRows extends PureComponent<any, {}> {
  render() {
    const { className = '', queries, queryErrors = [], queryHints = [], ...handlers } = this.props;
    return (
      <div className={className}>
        {queries.map((q, index) => (
          <QueryRow
            key={q.key}
            index={index}
            query={q.query}
            queryError={queryErrors[index]}
            queryHint={queryHints[index]}
            edited={q.edited}
            {...handlers}
          />
        ))}
      </div>
    );
  }
}
