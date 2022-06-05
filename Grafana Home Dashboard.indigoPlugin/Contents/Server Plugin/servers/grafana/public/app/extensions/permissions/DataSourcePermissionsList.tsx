import React from 'react';

import { Icon, LegacyForms } from '@grafana/ui';
import { dataSourceAclLevels, DataSourcePermissionLevel } from 'app/types/acl';

import { DataSourcePermission } from '../types';

const { Select } = LegacyForms;

export interface Props {
  items: DataSourcePermission[];
  onRemoveItem: (item: DataSourcePermission) => void;
}

const adminRole: DataSourcePermission = {
  id: -1,
  datasourceId: -1,
  updated: '',
  created: '',
  permissionName: 'Admin',
  builtInRole: 'Admin',
  permission: DataSourcePermissionLevel.Admin,
};

const adminLevel = {
  label: 'Admin',
  description: '',
  value: DataSourcePermissionLevel.Admin,
};

export const DataSourcePermissionsList = ({ items, onRemoveItem }: Props) => {
  const users = items.filter((i) => i.userId !== undefined);
  const teams = items.filter((i) => i.teamId !== undefined);
  const builtIns = [adminRole];

  return (
    <div>
      <PermissionTable title={'Roles'} items={builtIns} onRemove={onRemoveItem} />
      <PermissionTable title={'Users'} items={users} onRemove={onRemoveItem} />
      <PermissionTable title={'Teams'} items={teams} onRemove={onRemoveItem} />
    </div>
  );
};

interface PermissionTableProps {
  title: string;
  items: DataSourcePermission[];
  onRemove: (item: DataSourcePermission) => void;
}

const PermissionTable = ({ title, items, onRemove }: PermissionTableProps) => {
  if (items.length === 0) {
    return null;
  }

  return (
    <div>
      <h5>{title}</h5>
      <table className="filter-table gf-form-group">
        <tbody>
          {items.map((item, index) => (
            <TableRow key={`${index}-${item.id}`} item={item} onRemove={onRemove} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

interface TableRowProps {
  item: DataSourcePermission;
  onRemove: (item: DataSourcePermission) => void;
}

const TableRow = ({ item, onRemove }: TableRowProps) => {
  const renderAvatar = () => {
    if (item.teamId) {
      return <img className="filter-table__avatar" src={item.teamAvatarUrl} alt={`Avatar for team ${item.teamId}`} />;
    } else if (item.userId) {
      return <img className="filter-table__avatar" src={item.userAvatarUrl} alt={`Avatar for user ${item.userId}`} />;
    }
    return <Icon size="xl" name="shield" />;
  };

  const renderDescription = () => {
    if (item.userId) {
      return <span key="name">{item.userLogin} </span>;
    } else if (item.teamId) {
      return <span key="name">{item.team} </span>;
    } else if (item.builtInRole) {
      return <span key="name">{item.builtInRole} </span>;
    }
    return <span key="name" />;
  };

  const levels = [...dataSourceAclLevels, adminLevel];

  return (
    <tr>
      <td style={{ width: '1%' }}>{renderAvatar()}</td>
      <td style={{ width: '90%' }}>{renderDescription()}</td>
      <td />
      <td className="query-keyword">Can</td>
      <td>
        <div className="gf-form">
          <Select
            isDisabled={true}
            onChange={() => {}}
            options={levels}
            value={levels.find((level) => level.value === item.permission)}
          />
        </div>
      </td>
      <td>
        {item.builtInRole ? (
          <button className="btn btn-inverse btn-small">
            <Icon name="lock" size="sm" />
          </button>
        ) : (
          <button className="btn btn-danger btn-small" onClick={() => onRemove(item)}>
            <Icon name="times" size="sm" />
          </button>
        )}
      </td>
    </tr>
  );
};
