# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2011 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

# gtk is imported later (on demand)
#import gtk

import pycam.Plugins
import pycam.Geometry.Model


class ModelSupportGrid(pycam.Plugins.PluginBase):

    UI_FILE = "model_support_grid.ui"
    DEPENDS = ["Models", "ModelSupport"]
    CATEGORIES = ["Model", "Support bridges"]

    def setup(self):
        if self.gui:
            import gtk
            grid_box = self.gui.get_object("SupportModelGridBox")
            grid_box.unparent()
            self.core.register_ui("support_model_type_selector", "Grid",
                    "grid", weight=-10)
            self.core.register_ui("support_model_settings", "Grid settings",
                    grid_box)
            self.core.register_event("support-model-changed",
                    self.update_support_model)
            support_model_changed = lambda widget=None: self.core.emit_event(
                    "support-model-changed")
            # support grid
            self.grid_adjustments_x = []
            self.grid_adjustments_y = []
            self.grid_adjustment_axis_x_last = True
            self._block_manual_adjust_update = False
            grid_distance_x = self.gui.get_object("SupportGridDistanceX")
            grid_distance_x.connect("value-changed", support_model_changed)
            self.core.add_item("support_grid_distance_x",
                    grid_distance_x.get_value, grid_distance_x.set_value)
            grid_distance_square = self.gui.get_object("SupportGridDistanceSquare")
            grid_distance_square.connect("clicked", self.update_support_controls)
            grid_distance_y = self.gui.get_object("SupportGridDistanceY")
            grid_distance_y.connect("value-changed", support_model_changed)
            def get_support_grid_distance_y():
                if grid_distance_square.get_active():
                    return self.core.get("support_grid_distance_x")
                else:
                    return grid_distance_y.get_value()
            self.core.add_item("support_grid_distance_y",
                    get_support_grid_distance_y, grid_distance_y.set_value)
            grid_offset_x = self.gui.get_object("SupportGridOffsetX")
            grid_offset_x.connect("value-changed", support_model_changed)
            self.core.add_item("support_grid_offset_x",
                    grid_offset_x.get_value, grid_offset_x.set_value)
            grid_offset_y = self.gui.get_object("SupportGridOffsetY")
            grid_offset_y.connect("value-changed", support_model_changed)
            self.core.add_item("support_grid_offset_y",
                    grid_offset_y.get_value, grid_offset_y.set_value)
            # manual grid adjustments
            self.grid_adjustment_axis_x = self.gui.get_object("SupportGridPositionManualAxisX")
            self.grid_adjustment_axis_x.connect("toggled",
                    self.switch_support_grid_manual_selector)
            self.gui.get_object("SupportGridPositionManualResetOne").connect(
                    "clicked", self.reset_support_grid_manual, False)
            self.gui.get_object("SupportGridPositionManualResetAll").connect(
                    "clicked", self.reset_support_grid_manual, True)
            self.grid_adjustment_model = self.gui.get_object(
                    "SupportGridPositionManualList")
            self.grid_adjustment_selector = self.gui.get_object(
                    "SupportGridPositionManualSelector")
            self.grid_adjustment_selector.connect("changed",
                    self.switch_support_grid_manual_selector)
            self.grid_adjustment_value = self.gui.get_object(
                    "SupportGridPositionManualAdjustment")
            self.grid_adjustment_value_control = self.gui.get_object(
                    "SupportGridPositionManualShiftControl")
            self.grid_adjustment_value_control.set_update_policy(
                    gtk.UPDATE_DISCONTINUOUS)
            self.grid_adjustment_value_control.connect("move-slider",
                    self.update_support_grid_manual_adjust)
            self.grid_adjustment_value_control.connect("value-changed",
                    self.update_support_grid_manual_adjust)
            self.gui.get_object("SupportGridPositionManualShiftControl2").connect(
                    "value-changed", self.update_support_grid_manual_adjust)
            def get_set_grid_adjustment_value(value=None):
                if self.grid_adjustment_axis_x.get_active():
                    adjustments = self.grid_adjustments_x
                else:
                    adjustments = self.grid_adjustments_y
                index = self.grid_adjustment_selector.get_active()
                if value is None:
                    if 0 <= index < len(adjustments):
                        return adjustments[index]
                    else:
                        return 0
                else:
                    while len(adjustments) <= index:
                        adjustments.append(0)
                    adjustments[index] = value
            # TODO: remove these public settings
            self.core.add_item("support_grid_adjustment_value",
                    get_set_grid_adjustment_value, get_set_grid_adjustment_value)
            self.core.register_event("support-model-changed",
                    self.update_support_controls)
            grid_distance_square.set_active(True)
            self.core.set("support_grid_distance_x", 10.0)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("support_model_type_selector", "grid")
            self.core.unregister_ui("support_model_settings",
                    self.gui.get_object("SupportModelGridBox"))
            self.core.unregister_event("support-model-changed",
                    self.update_support_model)

    def update_support_model(self, widget=None):
        grid_type = self.core.get("support_model_type")
        if grid_type == "grid": 
            s = self.core
            support_grid = None
            low, high = self._get_bounds()
            if (s.get("support_grid_thickness") > 0) \
                    and ((s.get("support_grid_distance_x") > 0) \
                        or (s.get("support_grid_distance_y") > 0)) \
                    and ((s.get("support_grid_distance_x") == 0) \
                        or (s.get("support_grid_distance_x") \
                            > s.get("support_grid_thickness"))) \
                    and ((s.get("support_grid_distance_y") == 0) \
                        or (s.get("support_grid_distance_y") \
                            > s.get("support_grid_thickness"))) \
                    and (s.get("support_grid_height") > 0):
                support_grid = pycam.Toolpath.SupportGrid.get_support_grid(
                        low[0], high[0], low[1], high[1], low[2],
                        s.get("support_grid_distance_x"),
                        s.get("support_grid_distance_y"),
                        s.get("support_grid_thickness"),
                        s.get("support_grid_height"),
                        offset_x=s.get("support_grid_offset_x"),
                        offset_y=s.get("support_grid_offset_y"),
                        adjustments_x=self.grid_adjustments_x,
                        adjustments_y=self.grid_adjustments_y)
            self.core.set("current_support_model", support_grid)
            self.core.emit_event("visual-item-updated")

    def update_support_controls(self, widget=None):
        grid_type = self.core.get("support_model_type")
        if grid_type == "grid":
            grid_square = self.gui.get_object("SupportGridDistanceSquare")
            distance_y = self.gui.get_object("SupportGridDistanceYControl")
            distance_y.set_sensitive(not grid_square.get_active())
            if grid_square.get_active():
                # We let "distance_y" track the value of "distance_x".
                self.core.set("support_grid_distance_y",
                        self.core.get("support_grid_distance_x"))
            self.update_support_grid_manual_model()
            self.switch_support_grid_manual_selector()
            self.gui.get_object("SupportModelGridBox").show()
        else:
            self.gui.get_object("SupportModelGridBox").hide()

    def switch_support_grid_manual_selector(self, widget=None):
        """ Event handler for a switch between the x and y axis selector for
        manual adjustment. Final goal: update the adjustment combobox with the
        current values for that axis.
        """
        old_axis_was_x = self.grid_adjustment_axis_x_last
        self.grid_adjustment_axis_x_last = \
                self.grid_adjustment_axis_x.get_active()
        if self.grid_adjustment_axis_x.get_active():
            # x axis is selected
            if not old_axis_was_x:
                self.update_support_grid_manual_model()
            max_distance = self.core.get("support_grid_distance_x")
        else:
            # y axis
            if old_axis_was_x:
                self.update_support_grid_manual_model()
            max_distance = self.core.get("support_grid_distance_y")
        # we allow an individual adjustment of 66% of the distance
        max_distance /= 1.5
        if hasattr(self.grid_adjustment_value, "set_lower"):
            # gtk 2.14 is required for "set_lower" and "set_upper"
            self.grid_adjustment_value.set_lower(-max_distance)
            self.grid_adjustment_value.set_upper(max_distance)
        if self.grid_adjustment_value.get_value() \
                != self.core.get("support_grid_adjustment_value"):
            self.grid_adjustment_value.set_value(self.core.get(
                    "support_grid_adjustment_value"))
        self.gui.get_object("SupportGridPositionManualShiftBox").set_sensitive(
                self.grid_adjustment_selector.get_active() >= 0)
        
    def update_support_grid_manual_adjust(self, widget=None, data1=None,
            data2=None):
        """ Update the current entry in the manual adjustment combobox after
        a manual change. Additionally the slider and the numeric control are
        synched.
        """
        if self._block_manual_adjust_update:
            return
        self._block_manual_adjust_update = True
        new_value = self.grid_adjustment_value.get_value()
        self.core.set("support_grid_adjustment_value", new_value)
        tree_iter = self.grid_adjustment_selector.get_active_iter()
        if not tree_iter is None:
            value_string = "(%+.1f)" % new_value
            self.grid_adjustment_model.set(tree_iter, 1, value_string)
        self.core.emit_event("support-model-changed")
        self._block_manual_adjust_update = False

    def reset_support_grid_manual(self, widget=None, reset_all=False):
        if reset_all:
            self.grid_adjustments_x = []
            self.grid_adjustments_y = []
        else:
            self.core.set("support_grid_adjustment_value", 0)
        self.update_support_grid_manual_model()
        self.switch_support_grid_manual_selector()
        self.core.emit_event("support-model-changed")

    def update_support_grid_manual_model(self):
        old_index = self.grid_adjustment_selector.get_active()
        model = self.grid_adjustment_model
        model.clear()
        s = self.core
        # get the toolpath without adjustments
        low, high = self._get_bounds()
        base_x, base_y = pycam.Toolpath.SupportGrid.get_support_grid_locations(
                low[0], high[0], low[1], high[1],
                s.get("support_grid_distance_x"),
                s.get("support_grid_distance_y"),
                offset_x=s.get("support_grid_offset_x"),
                offset_y=s.get("support_grid_offset_y"))
        # fill the adjustment lists
        while len(self.grid_adjustments_x) < len(base_x):
            self.grid_adjustments_x.append(0)
        while len(self.grid_adjustments_y) < len(base_y):
            self.grid_adjustments_y.append(0)
        # select the currently active list
        if self.grid_adjustment_axis_x.get_active():
            base = base_x
            adjustments = self.grid_adjustments_x
        else:
            base = base_y
            adjustments = self.grid_adjustments_y
        # generate the model content
        for index, base_value in enumerate(base):
            position = "%.2f%s" % (base_value, s.get("unit"))
            if (0 <= index < len(adjustments)) and (adjustments[index] != 0):
                diff = "(%+.1f)" % adjustments[index]
            else:
                diff = ""
            model.append((position, diff))
        if old_index < len(base):
            self.grid_adjustment_selector.set_active(old_index)
        else:
            self.grid_adjustment_selector.set_active(-1)

    def _get_bounds(self):
        models = self.core.get("models").get_selected()
        low, high = pycam.Geometry.Model.get_combined_bounds(models)
        if None in low or None in high:
            return [0, 0, 0], [0, 0, 0]
        else:
            # TODO: the x/y offset should be configurable via a control
            for index in range(2):
                low[index] -= 5
                high[index] += 5
            return low, high