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
import json
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
        item_data = item.__dict__['data']
        if type(item.info) == dict:
            keys = item_data['info'].keys()
            for k in keys:
                item_data[k] = item_data['info'][k]
        return item_data

    def get_tasks(self, task_id=None, state='completed', json_file=None):
        """Load all project Tasks."""
        if self.project is None:
            raise ProjectError
        if task_id:
            offset = 0
            limit = 1
            query = dict(project_id=self.project.id,
                         state=state,
                         id=task_id,
                         limit=limit,
                         offset=offset)
        else:
            offset = 0
            limit = 100
            query = dict(project_id=self.project.id,
                         state=state,
                         limit=limit,
                         offset=offset)
        self.tasks = []

        if json_file:
            json_file_data = open(json_file).read()
            file_tasks = json.loads(json_file_data)
            for t in file_tasks:
                self.tasks.append(pbclient.Task(t))
        else:
            tasks = pbclient.find_tasks(**query)
            while(len(tasks) != 0):
                self.tasks += tasks
                offset += limit
                query['offset'] += limit
                tasks = pbclient.find_tasks(**query)

        # Create the data frame for tasks
        try:
            self.tasks[0]
            data = [self.explode_info(t) for t in self.tasks]
            index = [t.__dict__['data']['id'] for t in self.tasks]
            self.tasks_df = pandas.DataFrame(data, index)
        except:
            raise ProjectWithoutTasks

    def get_task_runs(self, json_file=None):
        """Load all project Task Runs from Tasks."""
        if self.project is None:
            raise ProjectError
        self.task_runs = {}
        self.task_runs_file = []
        self.task_runs_df = {}

        if json_file:
            self._load_task_runs_from_file(json_file)
        else:
            self._load_task_runs_from_server()
        self._check_project_has_taskruns()

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

    def _load_task_runs_from_file(self, json_file):
        self._load_from_json(json_file)
        self._group_json_task_runs_by_task_id()

    def _load_from_json(self, json_file):
        json_file_data = open(json_file).read()
        file_task_runs = json.loads(json_file_data)
        for tr in file_task_runs:
            self.task_runs_file.append(pbclient.TaskRun(tr))

    def _group_json_task_runs_by_task_id(self):
        for t in self.tasks:
            self.task_runs[t.id] = [tr for tr in self.task_runs_file
                                    if (tr.task_id == t.id
                                        and
                                        tr.project_id == self.project.id)]
            self._create_task_run_dfs(t.id)

    def _load_task_runs_from_server(self):
        for t in self.tasks:
            offset = 0
            limit = 100
            self.task_runs[t.id] = []
            taskruns = pbclient.find_taskruns(project_id=self.project.id,
                                              task_id=t.id,
                                              limit=limit,
                                              offset=offset)
            while(len(taskruns) != 0):
                self.task_runs[t.id] += taskruns
                offset += limit
                taskruns = pbclient.find_taskruns(
                    project_id=self.project.id,
                    task_id=t.id,
                    limit=limit,
                    offset=offset)
            self._create_task_run_dfs(t.id)

    def _create_task_run_dfs(self, task_id):
        data = [self.explode_info(tr)
                for tr in self.task_runs[task_id]]
        index = [tr.__dict__['data']['id'] for tr in
                 self.task_runs[task_id]]
        self.task_runs_df[task_id] = pandas.DataFrame(data, index)

    def _check_project_has_taskruns(self):
        add_number_task_runs = lambda total, task_runs: total + len(task_runs)
        total_task_runs = reduce(add_number_task_runs, self.task_runs.values(), 0)
        if total_task_runs == 0:
            raise ProjectWithoutTaskRuns
