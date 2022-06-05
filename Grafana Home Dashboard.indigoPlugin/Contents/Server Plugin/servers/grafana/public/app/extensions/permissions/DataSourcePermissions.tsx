import React, { PureComponent } from 'react';
import { connect, ConnectedProps } from 'react-redux';

import { Alert, Button } from '@grafana/ui';
import { SlideDown } from 'app/core/components/Animations/SlideDown';
import EmptyListCTA from 'app/core/components/EmptyListCTA/EmptyListCTA';
import PageHeader from 'app/core/components/PageHeader/PageHeader';
import { UpgradeBox } from 'app/core/components/Upgrade/UpgradeBox';
import { GrafanaRouteComponentProps } from 'app/core/navigation/types';
import { getNavModel } from 'app/core/selectors/navModel';
import { highlightTrial } from 'app/features/admin/utils';
import { loadDataSource, loadDataSourceMeta } from 'app/features/datasources/state/actions';
import { getDataSourceLoadingNav } from 'app/features/datasources/state/navModel';
import { AclTarget } from 'app/types';

import { DataSourcePermission, EnterpriseStoreState } from '../types';

import { AddDataSourcePermissions, State as AddState } from './AddDataSourcePermissions';
import { DataSourcePermissionsList } from './DataSourcePermissionsList';
import { PermissionsUpgradeContent } from './UpgradePage';
import {
  addDataSourcePermission,
  disableDataSourcePermissions,
  enableDataSourcePermissions,
  loadDataSourcePermissions,
  removeDataSourcePermission,
} from './state/actions';

interface RouteProps extends GrafanaRouteComponentProps<{ uid: string }> {}

function mapStateToProps(state: EnterpriseStoreState, props: RouteProps) {
  const uid = props.match.params.uid;
  const dataSourceLoadingNav = getDataSourceLoadingNav('permissions');
  return {
    uid,
    enabled: state.dataSourcePermission.enabled,
    isDefault: state.dataSources.dataSource.isDefault,
    permissions: state.dataSourcePermission.permissions,
    navModel: getNavModel(state.navIndex, `datasource-permissions-${uid}`, dataSourceLoadingNav),
  };
}

const mapDispatchToProps = {
  addDataSourcePermission,
  enableDataSourcePermissions,
  disableDataSourcePermissions,
  loadDataSourcePermissions,
  loadDataSource,
  loadDataSourceMeta,
  removeDataSourcePermission,
};

const connector = connect(mapStateToProps, mapDispatchToProps);

export type Props = ConnectedProps<typeof connector>;

interface State {
  isAdding: boolean;
  datasourceId: number;
}

export class DataSourcePermissions extends PureComponent<Props, State> {
  state: State = {
    datasourceId: 0,
    isAdding: false,
  };

  componentDidMount() {
    this.fetchDataSource().then((ds) => {
      this.props.loadDataSourceMeta(ds);
      this.setState({ datasourceId: ds.id });
      this.fetchDataSourcePermissions(ds.id);
    });
  }

  async fetchDataSource() {
    const { uid, loadDataSource } = this.props;
    return loadDataSource(uid);
  }

  async fetchDataSourcePermissions(id: number) {
    const { loadDataSourcePermissions } = this.props;
    return loadDataSourcePermissions(id);
  }

  onOpenAddPermissions = () => {
    this.setState({
      isAdding: true,
    });
  };

  onEnablePermissions = () => {
    const { enableDataSourcePermissions } = this.props;
    enableDataSourcePermissions(this.state.datasourceId);
  };

  onDisablePermissions = () => {
    const { disableDataSourcePermissions } = this.props;
    disableDataSourcePermissions(this.state.datasourceId);
  };

  onAddPermission = (state: AddState) => {
    const { addDataSourcePermission } = this.props;
    const data = { permission: state.permission };

    if (state.type === AclTarget.Team) {
      addDataSourcePermission(this.state.datasourceId, Object.assign(data, { teamId: state.teamId }));
    } else if (state.type === AclTarget.User) {
      addDataSourcePermission(this.state.datasourceId, Object.assign(data, { userId: state.userId }));
    }
  };

  onRemovePermission = (item: DataSourcePermission) => {
    this.props.removeDataSourcePermission(item.datasourceId, item.id);
  };

  onCancelAddPermission = () => {
    this.setState({
      isAdding: false,
    });
  };

  isEnabled = () => {
    return this.props.enabled;
  };

  renderActions = () => {
    const actions = [];
    const { isAdding } = this.state;

    if (this.isEnabled()) {
      actions.push(
        <Button variant={'primary'} key="add-permission" onClick={this.onOpenAddPermissions} disabled={isAdding}>
          Add a permission
        </Button>
      );

      actions.push(
        <Button variant={'destructive'} key="disable-permissions" onClick={this.onDisablePermissions}>
          Disable permissions
        </Button>
      );
    }

    return actions;
  };

  render() {
    const { permissions, navModel, isDefault } = this.props;
    const { isAdding } = this.state;

    return (
      <div>
        <PageHeader model={navModel} />
        <div className="page-container page-body">
          {highlightTrial() && (
            <UpgradeBox
              featureId={'data-source-permissions'}
              eventVariant={'trial'}
              featureName={'data source permissions'}
              text={'Enable data source permissions for free during your trial of Grafana Pro.'}
            />
          )}
          <div className="page-action-bar">
            <h3 className="page-sub-heading">Permissions</h3>
            <div className="page-action-bar__spacer" />
            {this.renderActions()}
          </div>
          {isDefault && !this.isEnabled() && (
            <Alert title="Warning!">
              Enabling permissions on the default data source makes it unavailable for users not listed in the
              permissions.
            </Alert>
          )}
          {!this.isEnabled() ? (
            highlightTrial() ? (
              <PermissionsUpgradeContent action={{ onClick: this.onEnablePermissions, text: 'Enable permissions' }} />
            ) : (
              <EmptyListCTA
                title="Permissions not enabled for this data source."
                buttonTitle="Enable"
                buttonIcon="unlock"
                onClick={this.onEnablePermissions}
                proTip="Only admins will be able to query the data source after you enable permissions."
                proTipLink="https://docs.grafana.org/permissions/datasource_permissions/"
                proTipLinkTitle="Learn more"
              />
            )
          ) : (
            <div>
              <SlideDown in={isAdding}>
                <AddDataSourcePermissions
                  onAddPermission={(state) => this.onAddPermission(state)}
                  onCancel={this.onCancelAddPermission}
                />
              </SlideDown>
              <DataSourcePermissionsList items={permissions} onRemoveItem={this.onRemovePermission} />
            </div>
          )}
        </div>
      </div>
    );
  }
}

export default connector(DataSourcePermissions);
