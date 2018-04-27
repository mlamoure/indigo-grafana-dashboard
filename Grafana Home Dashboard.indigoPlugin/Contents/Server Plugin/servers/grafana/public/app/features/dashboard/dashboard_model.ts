import moment from 'moment';
import _ from 'lodash';

import { GRID_COLUMN_COUNT, REPEAT_DIR_VERTICAL } from 'app/core/constants';
import { DEFAULT_ANNOTATION_COLOR } from 'app/core/utils/colors';
import { Emitter } from 'app/core/utils/emitter';
import { contextSrv } from 'app/core/services/context_srv';
import sortByKeys from 'app/core/utils/sort_by_keys';

import { PanelModel } from './panel_model';
import { DashboardMigrator } from './dashboard_migration';

export class DashboardModel {
  id: any;
  uid: any;
  title: any;
  autoUpdate: any;
  description: any;
  tags: any;
  style: any;
  timezone: any;
  editable: any;
  graphTooltip: any;
  time: any;
  timepicker: any;
  templating: any;
  annotations: any;
  refresh: any;
  snapshot: any;
  schemaVersion: number;
  version: number;
  revision: number;
  links: any;
  gnetId: any;
  panels: PanelModel[];

  // ------------------
  // not persisted
  // ------------------

  // repeat process cycles
  iteration: number;
  meta: any;
  events: Emitter;

  static nonPersistedProperties: { [str: string]: boolean } = {
    events: true,
    meta: true,
    panels: true, // needs special handling
    templating: true, // needs special handling
  };

  constructor(data, meta?) {
    if (!data) {
      data = {};
    }

    this.events = new Emitter();
    this.id = data.id || null;
    this.uid = data.uid || null;
    this.revision = data.revision;
    this.title = data.title || 'No Title';
    this.autoUpdate = data.autoUpdate;
    this.description = data.description;
    this.tags = data.tags || [];
    this.style = data.style || 'dark';
    this.timezone = data.timezone || '';
    this.editable = data.editable !== false;
    this.graphTooltip = data.graphTooltip || 0;
    this.time = data.time || { from: 'now-6h', to: 'now' };
    this.timepicker = data.timepicker || {};
    this.templating = this.ensureListExist(data.templating);
    this.annotations = this.ensureListExist(data.annotations);
    this.refresh = data.refresh;
    this.snapshot = data.snapshot;
    this.schemaVersion = data.schemaVersion || 0;
    this.version = data.version || 0;
    this.links = data.links || [];
    this.gnetId = data.gnetId || null;
    this.panels = _.map(data.panels || [], panelData => new PanelModel(panelData));

    this.initMeta(meta);
    this.updateSchema(data);

    this.addBuiltInAnnotationQuery();
    this.sortPanelsByGridPos();
  }

  addBuiltInAnnotationQuery() {
    let found = false;
    for (let item of this.annotations.list) {
      if (item.builtIn === 1) {
        found = true;
        break;
      }
    }

    if (found) {
      return;
    }

    this.annotations.list.unshift({
      datasource: '-- Grafana --',
      name: 'Annotations & Alerts',
      type: 'dashboard',
      iconColor: DEFAULT_ANNOTATION_COLOR,
      enable: true,
      hide: true,
      builtIn: 1,
    });
  }

  private initMeta(meta) {
    meta = meta || {};

    meta.canShare = meta.canShare !== false;
    meta.canSave = meta.canSave !== false;
    meta.canStar = meta.canStar !== false;
    meta.canEdit = meta.canEdit !== false;
    meta.showSettings = meta.canEdit;
    meta.canMakeEditable = meta.canSave && !this.editable;

    if (!this.editable) {
      meta.canEdit = false;
      meta.canDelete = false;
      meta.canSave = false;
    }

    this.meta = meta;
  }

  // cleans meta data and other non persistent state
  getSaveModelClone() {
    // make clone
    var copy: any = {};
    for (var property in this) {
      if (DashboardModel.nonPersistedProperties[property] || !this.hasOwnProperty(property)) {
        continue;
      }

      copy[property] = _.cloneDeep(this[property]);
    }

    // get variable save models
    copy.templating = {
      list: _.map(this.templating.list, variable => (variable.getSaveModel ? variable.getSaveModel() : variable)),
    };

    // get panel save models
    copy.panels = _.chain(this.panels)
      .filter(panel => panel.type !== 'add-panel')
      .map(panel => panel.getSaveModel())
      .value();

    //  sort by keys
    copy = sortByKeys(copy);

    return copy;
  }

  setViewMode(panel: PanelModel, fullscreen: boolean, isEditing: boolean) {
    this.meta.fullscreen = fullscreen;
    this.meta.isEditing = isEditing && this.meta.canEdit;

    panel.setViewMode(fullscreen, this.meta.isEditing);

    this.events.emit('view-mode-changed', panel);
  }

  private ensureListExist(data) {
    if (!data) {
      data = {};
    }
    if (!data.list) {
      data.list = [];
    }
    return data;
  }

  getNextPanelId() {
    let max = 0;

    for (let panel of this.panels) {
      if (panel.id > max) {
        max = panel.id;
      }

      if (panel.collapsed) {
        for (let rowPanel of panel.panels) {
          if (rowPanel.id > max) {
            max = rowPanel.id;
          }
        }
      }
    }

    return max + 1;
  }

  forEachPanel(callback) {
    for (let i = 0; i < this.panels.length; i++) {
      callback(this.panels[i], i);
    }
  }

  getPanelById(id) {
    for (let panel of this.panels) {
      if (panel.id === id) {
        return panel;
      }
    }
    return null;
  }

  addPanel(panelData) {
    panelData.id = this.getNextPanelId();

    let panel = new PanelModel(panelData);

    this.panels.unshift(panel);

    this.sortPanelsByGridPos();

    this.events.emit('panel-added', panel);
  }

  sortPanelsByGridPos() {
    this.panels.sort(function(panelA, panelB) {
      if (panelA.gridPos.y === panelB.gridPos.y) {
        return panelA.gridPos.x - panelB.gridPos.x;
      } else {
        return panelA.gridPos.y - panelB.gridPos.y;
      }
    });
  }

  cleanUpRepeats() {
    if (this.snapshot || this.templating.list.length === 0) {
      return;
    }

    this.iteration = (this.iteration || new Date().getTime()) + 1;
    let panelsToRemove = [];

    // cleanup scopedVars
    for (let panel of this.panels) {
      delete panel.scopedVars;
    }

    for (let i = 0; i < this.panels.length; i++) {
      let panel = this.panels[i];
      if ((!panel.repeat || panel.repeatedByRow) && panel.repeatPanelId && panel.repeatIteration !== this.iteration) {
        panelsToRemove.push(panel);
      }
    }

    // remove panels
    _.pull(this.panels, ...panelsToRemove);

    this.sortPanelsByGridPos();
    this.events.emit('repeats-processed');
  }

  processRepeats() {
    if (this.snapshot || this.templating.list.length === 0) {
      return;
    }

    this.cleanUpRepeats();

    this.iteration = (this.iteration || new Date().getTime()) + 1;

    for (let i = 0; i < this.panels.length; i++) {
      let panel = this.panels[i];
      if (panel.repeat) {
        this.repeatPanel(panel, i);
      }
    }

    this.sortPanelsByGridPos();
    this.events.emit('repeats-processed');
  }

  cleanUpRowRepeats(rowPanels) {
    let panelsToRemove = [];
    for (let i = 0; i < rowPanels.length; i++) {
      let panel = rowPanels[i];
      if (!panel.repeat && panel.repeatPanelId) {
        panelsToRemove.push(panel);
      }
    }
    _.pull(rowPanels, ...panelsToRemove);
    _.pull(this.panels, ...panelsToRemove);
  }

  processRowRepeats(row: PanelModel) {
    if (this.snapshot || this.templating.list.length === 0) {
      return;
    }

    let rowPanels = row.panels;
    if (!row.collapsed) {
      let rowPanelIndex = _.findIndex(this.panels, p => p.id === row.id);
      rowPanels = this.getRowPanels(rowPanelIndex);
    }

    this.cleanUpRowRepeats(rowPanels);

    for (let i = 0; i < rowPanels.length; i++) {
      let panel = rowPanels[i];
      if (panel.repeat) {
        let panelIndex = _.findIndex(this.panels, p => p.id === panel.id);
        this.repeatPanel(panel, panelIndex);
      }
    }
  }

  getPanelRepeatClone(sourcePanel, valueIndex, sourcePanelIndex) {
    // if first clone return source
    if (valueIndex === 0) {
      return sourcePanel;
    }

    let clone = new PanelModel(sourcePanel.getSaveModel());
    clone.id = this.getNextPanelId();

    // insert after source panel + value index
    this.panels.splice(sourcePanelIndex + valueIndex, 0, clone);

    clone.repeatIteration = this.iteration;
    clone.repeatPanelId = sourcePanel.id;
    clone.repeat = null;
    return clone;
  }

  getRowRepeatClone(sourceRowPanel, valueIndex, sourcePanelIndex) {
    // if first clone return source
    if (valueIndex === 0) {
      if (!sourceRowPanel.collapsed) {
        let rowPanels = this.getRowPanels(sourcePanelIndex);
        sourceRowPanel.panels = rowPanels;
      }
      return sourceRowPanel;
    }

    let clone = new PanelModel(sourceRowPanel.getSaveModel());
    // for row clones we need to figure out panels under row to clone and where to insert clone
    let rowPanels, insertPos;
    if (sourceRowPanel.collapsed) {
      rowPanels = _.cloneDeep(sourceRowPanel.panels);
      clone.panels = rowPanels;
      // insert copied row after preceding row
      insertPos = sourcePanelIndex + valueIndex;
    } else {
      rowPanels = this.getRowPanels(sourcePanelIndex);
      clone.panels = _.map(rowPanels, panel => panel.getSaveModel());
      // insert copied row after preceding row's panels
      insertPos = sourcePanelIndex + (rowPanels.length + 1) * valueIndex;
    }
    this.panels.splice(insertPos, 0, clone);

    this.updateRepeatedPanelIds(clone);
    return clone;
  }

  repeatPanel(panel: PanelModel, panelIndex: number) {
    let variable = _.find(this.templating.list, { name: panel.repeat });
    if (!variable) {
      return;
    }

    if (panel.type === 'row') {
      this.repeatRow(panel, panelIndex, variable);
      return;
    }

    let selectedOptions = this.getSelectedVariableOptions(variable);
    let minWidth = panel.minSpan || 6;
    let xPos = 0;
    let yPos = panel.gridPos.y;

    for (let index = 0; index < selectedOptions.length; index++) {
      let option = selectedOptions[index];
      let copy;

      copy = this.getPanelRepeatClone(panel, index, panelIndex);
      copy.scopedVars = copy.scopedVars || {};
      copy.scopedVars[variable.name] = option;

      if (panel.repeatDirection === REPEAT_DIR_VERTICAL) {
        if (index > 0) {
          yPos += copy.gridPos.h;
        }
        copy.gridPos.y = yPos;
      } else {
        // set width based on how many are selected
        // assumed the repeated panels should take up full row width
        copy.gridPos.w = Math.max(GRID_COLUMN_COUNT / selectedOptions.length, minWidth);
        copy.gridPos.x = xPos;
        copy.gridPos.y = yPos;

        xPos += copy.gridPos.w;

        // handle overflow by pushing down one row
        if (xPos + copy.gridPos.w > GRID_COLUMN_COUNT) {
          xPos = 0;
          yPos += copy.gridPos.h;
        }
      }
    }

    // Update gridPos for panels below
    let yOffset = yPos - panel.gridPos.y;
    if (yOffset > 0) {
      let panelBelowIndex = panelIndex + selectedOptions.length;
      for (let i = panelBelowIndex; i < this.panels.length; i++) {
        this.panels[i].gridPos.y += yOffset;
      }
    }
  }

  repeatRow(panel: PanelModel, panelIndex: number, variable) {
    let selectedOptions = this.getSelectedVariableOptions(variable);
    let yPos = panel.gridPos.y;

    function setScopedVars(panel, variableOption) {
      panel.scopedVars = panel.scopedVars || {};
      panel.scopedVars[variable.name] = variableOption;
    }

    for (let optionIndex = 0; optionIndex < selectedOptions.length; optionIndex++) {
      let option = selectedOptions[optionIndex];
      let rowCopy = this.getRowRepeatClone(panel, optionIndex, panelIndex);
      setScopedVars(rowCopy, option);

      let rowHeight = this.getRowHeight(rowCopy);
      let rowPanels = rowCopy.panels || [];
      let panelBelowIndex;

      if (panel.collapsed) {
        // For collapsed row just copy its panels and set scoped vars and proper IDs
        _.each(rowPanels, (rowPanel, i) => {
          setScopedVars(rowPanel, option);
          if (optionIndex > 0) {
            this.updateRepeatedPanelIds(rowPanel, true);
          }
        });
        rowCopy.gridPos.y += optionIndex;
        yPos += optionIndex;
        panelBelowIndex = panelIndex + optionIndex + 1;
      } else {
        // insert after 'row' panel
        let insertPos = panelIndex + (rowPanels.length + 1) * optionIndex + 1;
        _.each(rowPanels, (rowPanel, i) => {
          setScopedVars(rowPanel, option);
          if (optionIndex > 0) {
            let cloneRowPanel = new PanelModel(rowPanel);
            this.updateRepeatedPanelIds(cloneRowPanel, true);
            // For exposed row additionally set proper Y grid position and add it to dashboard panels
            cloneRowPanel.gridPos.y += rowHeight * optionIndex;
            this.panels.splice(insertPos + i, 0, cloneRowPanel);
          }
        });
        rowCopy.panels = [];
        rowCopy.gridPos.y += rowHeight * optionIndex;
        yPos += rowHeight;
        panelBelowIndex = insertPos + rowPanels.length;
      }

      // Update gridPos for panels below
      for (let i = panelBelowIndex; i < this.panels.length; i++) {
        this.panels[i].gridPos.y += yPos;
      }
    }
  }

  updateRepeatedPanelIds(panel: PanelModel, repeatedByRow?: boolean) {
    panel.repeatPanelId = panel.id;
    panel.id = this.getNextPanelId();
    panel.repeatIteration = this.iteration;
    if (repeatedByRow) {
      panel.repeatedByRow = true;
    } else {
      panel.repeat = null;
    }
    return panel;
  }

  getSelectedVariableOptions(variable) {
    let selectedOptions;
    if (variable.current.text === 'All') {
      selectedOptions = variable.options.slice(1, variable.options.length);
    } else {
      selectedOptions = _.filter(variable.options, { selected: true });
    }
    return selectedOptions;
  }

  getRowHeight(rowPanel: PanelModel): number {
    if (!rowPanel.panels || rowPanel.panels.length === 0) {
      return 0;
    }
    const rowYPos = rowPanel.gridPos.y;
    const positions = _.map(rowPanel.panels, 'gridPos');
    const maxPos = _.maxBy(positions, pos => {
      return pos.y + pos.h;
    });
    return maxPos.y + maxPos.h - rowYPos;
  }

  removePanel(panel: PanelModel) {
    var index = _.indexOf(this.panels, panel);
    this.panels.splice(index, 1);
    this.events.emit('panel-removed', panel);
  }

  removeRow(row: PanelModel, removePanels: boolean) {
    const needToogle = (!removePanels && row.collapsed) || (removePanels && !row.collapsed);

    if (needToogle) {
      this.toggleRow(row);
    }

    this.removePanel(row);
  }

  expandRows() {
    for (let i = 0; i < this.panels.length; i++) {
      var panel = this.panels[i];

      if (panel.type !== 'row') {
        continue;
      }

      if (panel.collapsed) {
        this.toggleRow(panel);
      }
    }
  }

  collapseRows() {
    for (let i = 0; i < this.panels.length; i++) {
      var panel = this.panels[i];

      if (panel.type !== 'row') {
        continue;
      }

      if (!panel.collapsed) {
        this.toggleRow(panel);
      }
    }
  }

  setPanelFocus(id) {
    this.meta.focusPanelId = id;
  }

  updateSubmenuVisibility() {
    this.meta.submenuEnabled = (() => {
      if (this.links.length > 0) {
        return true;
      }

      var visibleVars = _.filter(this.templating.list, variable => variable.hide !== 2);
      if (visibleVars.length > 0) {
        return true;
      }

      var visibleAnnotations = _.filter(this.annotations.list, annotation => annotation.hide !== true);
      if (visibleAnnotations.length > 0) {
        return true;
      }

      return false;
    })();
  }

  getPanelInfoById(panelId) {
    for (let i = 0; i < this.panels.length; i++) {
      if (this.panels[i].id === panelId) {
        return {
          panel: this.panels[i],
          index: i,
        };
      }
    }

    return null;
  }

  duplicatePanel(panel) {
    const newPanel = panel.getSaveModel();
    newPanel.id = this.getNextPanelId();

    delete newPanel.repeat;
    delete newPanel.repeatIteration;
    delete newPanel.repeatPanelId;
    delete newPanel.scopedVars;
    if (newPanel.alert) {
      delete newPanel.thresholds;
    }
    delete newPanel.alert;

    // does it fit to the right?
    if (panel.gridPos.x + panel.gridPos.w * 2 <= GRID_COLUMN_COUNT) {
      newPanel.gridPos.x += panel.gridPos.w;
    } else {
      // add below
      newPanel.gridPos.y += panel.gridPos.h;
    }

    this.addPanel(newPanel);
    return newPanel;
  }

  formatDate(date, format?) {
    date = moment.isMoment(date) ? date : moment(date);
    format = format || 'YYYY-MM-DD HH:mm:ss';
    let timezone = this.getTimezone();

    return timezone === 'browser' ? moment(date).format(format) : moment.utc(date).format(format);
  }

  destroy() {
    this.events.removeAllListeners();
    for (let panel of this.panels) {
      panel.destroy();
    }
  }

  toggleRow(row: PanelModel) {
    let rowIndex = _.indexOf(this.panels, row);

    if (row.collapsed) {
      row.collapsed = false;
      let hasRepeat = _.some(row.panels, p => p.repeat);

      if (row.panels.length > 0) {
        // Use first panel to figure out if it was moved or pushed
        let firstPanel = row.panels[0];
        let yDiff = firstPanel.gridPos.y - (row.gridPos.y + row.gridPos.h);

        // start inserting after row
        let insertPos = rowIndex + 1;
        // y max will represent the bottom y pos after all panels have been added
        // needed to know home much panels below should be pushed down
        let yMax = row.gridPos.y;

        for (let panel of row.panels) {
          // make sure y is adjusted (in case row moved while collapsed)
          // console.log('yDiff', yDiff);
          panel.gridPos.y -= yDiff;
          // insert after row
          this.panels.splice(insertPos, 0, new PanelModel(panel));
          // update insert post and y max
          insertPos += 1;
          yMax = Math.max(yMax, panel.gridPos.y + panel.gridPos.h);
        }

        const pushDownAmount = yMax - row.gridPos.y - 1;

        // push panels below down
        for (let panelIndex = insertPos; panelIndex < this.panels.length; panelIndex++) {
          this.panels[panelIndex].gridPos.y += pushDownAmount;
        }

        row.panels = [];

        if (hasRepeat) {
          this.processRowRepeats(row);
        }
      }

      // sort panels
      this.sortPanelsByGridPos();

      // emit change event
      this.events.emit('row-expanded');
      return;
    }

    let rowPanels = this.getRowPanels(rowIndex);

    // remove panels
    _.pull(this.panels, ...rowPanels);
    // save panel models inside row panel
    row.panels = _.map(rowPanels, panel => panel.getSaveModel());
    row.collapsed = true;

    // emit change event
    this.events.emit('row-collapsed');
  }

  /**
   * Will return all panels after rowIndex until it encounters another row
   */
  getRowPanels(rowIndex: number): PanelModel[] {
    let rowPanels = [];

    for (let index = rowIndex + 1; index < this.panels.length; index++) {
      let panel = this.panels[index];

      // break when encountering another row
      if (panel.type === 'row') {
        break;
      }

      // this panel must belong to row
      rowPanels.push(panel);
    }

    return rowPanels;
  }

  on(eventName, callback) {
    this.events.on(eventName, callback);
  }

  off(eventName, callback?) {
    this.events.off(eventName, callback);
  }

  cycleGraphTooltip() {
    this.graphTooltip = (this.graphTooltip + 1) % 3;
  }

  sharedTooltipModeEnabled() {
    return this.graphTooltip > 0;
  }

  sharedCrosshairModeOnly() {
    return this.graphTooltip === 1;
  }

  getRelativeTime(date) {
    date = moment.isMoment(date) ? date : moment(date);

    return this.timezone === 'browser' ? moment(date).fromNow() : moment.utc(date).fromNow();
  }

  getNextQueryLetter(panel) {
    var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

    return _.find(letters, function(refId) {
      return _.every(panel.targets, function(other) {
        return other.refId !== refId;
      });
    });
  }

  isTimezoneUtc() {
    return this.getTimezone() === 'utc';
  }

  getTimezone() {
    return this.timezone ? this.timezone : contextSrv.user.timezone;
  }

  private updateSchema(old) {
    let migrator = new DashboardMigrator(this);
    migrator.updateSchema(old);
  }
}
