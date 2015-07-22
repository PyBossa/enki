# -*- coding: utf8 -*-
# This file is part of PyBossa.
#
# Copyright (C) 2015 SF Isle of Man Limited
#
# PyBossa is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBossa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBossa.  If not, see <http://www.gnu.org/licenses/>.
"""
Enki module for analyzing the results of a PyBossa project.

This module exports:
    * Enki Class: to import an project, its tasks and task runs

"""
import pandas
import pbclient
from task_loaders import ServerTasksLoader, JsonTasksLoader
from task_run_loaders import ServerTaskRunsLoader, JsonTaskRunsLoader
from exceptions import ProjectNotFound, ProjectError, \
    ProjectWithoutTasks, ProjectWithoutTaskRuns


class Enki(object):

    """General class for Enki."""

    def __init__(self, api_key, endpoint, project_short_name):
        """Initiate."""
        self.project = None
        pbclient.set('api_key', api_key)
        pbclient.set('endpoint', endpoint)
        if self.project is None:
            self.project = self.get_project(project_short_name)

    def get_project(self, project_short_name):
        """Return project object."""
        project = pbclient.find_project(short_name=project_short_name)
        if (len(project) == 1):
            return project[0]
        else:
            raise ProjectNotFound(project_short_name)

    def explode_info(self, item):
        """Return the a dict of the object but with info field exploded."""
        return DataFrameFactory().explode_info(item)

    def get_tasks(self, task_id=None, state='completed', json_file=None):
        """Load all project Tasks."""
        if self.project is None:
            raise ProjectError

        loader = self._create_tasks_loader(task_id, state, json_file)
        self.tasks = loader.load()

        self._check_project_has_tasks()
        self.tasks_df = DataFrameFactory().create_data_frame(self.tasks)

    def get_task_runs(self, json_file=None):
        """Load all project Task Runs from Tasks."""
        if self.project is None:
            raise ProjectError
        loader = self._create_task_runs_loader(json_file)
        self.task_runs, self.task_runs_file = loader.load()

        self._check_project_has_taskruns()
        self.task_runs_df = DataFrameFactory().create_task_run_data_frames(self.tasks, self.task_runs)

    def get_all(self):  # pragma: no cover
        """Get task and task_runs from project."""
        self.get_tasks()
        self.get_task_runs()

    def describe(self, element):  # pragma: no cover
        """Return tasks or task_runs Panda describe."""
        if (element == 'tasks'):
            return self.tasks_df.describe()
        elif (element == 'task_runs'):
            return self.task_runs_df.describe()
        else:
            return "ERROR: %s not found" % element

    def _check_project_has_tasks(self):
        if len(self.tasks) == 0:
            raise ProjectWithoutTasks

    def _check_project_has_taskruns(self):
        add_number_task_runs = lambda total, task_runs: total + len(task_runs)
        total_task_runs = reduce(add_number_task_runs, self.task_runs.values(), 0)
        if total_task_runs == 0:
            raise ProjectWithoutTaskRuns

    def _create_tasks_loader(self, task_id, state, json_file):
        if json_file is not None:
            return JsonTasksLoader(json_file, self.project.id, task_id, state)
        return ServerTasksLoader(self.project.id, task_id, state)

    def _create_task_runs_loader(self, json_file):
        if json_file is not None:
            return JsonTaskRunsLoader(self.project.id, self.tasks, json_file)
        return ServerTaskRunsLoader(self.project.id, self.tasks)


class DataFrameFactory(object):

    def create_task_run_data_frames(self, tasks, task_runs):
        task_runs_df = {}
        for task in tasks:
            task_runs_df[task.id] = self.create_data_frame(task_runs[task.id])
        return task_runs_df

    def create_data_frame(self, item):
        data = [self.explode_info(tr) for tr in item]
        index = [tr.__dict__['data']['id'] for tr in item]
        return pandas.DataFrame(data, index)

    def explode_info(self, item):
        item_data = item.__dict__['data']
        if type(item.info) == dict:
            keys = item_data['info'].keys()
            for k in keys:
                item_data[k] = item_data['info'][k]
        return item_data
