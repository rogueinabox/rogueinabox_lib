# Copyright (C) 2017 Andrea Asperti, Carlo De Pieri, Gianmaria Pedrini
#
# This file is part of Rogueinabox.
#
# Rogueinabox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Rogueinabox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from shutil import copyfile

from os import path, remove


class SaveManager:
    """Used in conjunction with a judge, this class is used to save and organize test results."""

    def __init__(self, config, judge):
        self.config = config
        self.judge = judge
        self.assets_dir = config["assets_dir"]
        self.saves_dir = config["saves_dir"]
        self.last_name = ""

    def save_training(self):
        self.mode = "train"
        self.weights = self.last_name
        self.init_time = self.config["init_time"]
        self._init_dir(self.assets_dir)
        self._init_dir(self.saves_dir)
        self.id = self._get_new_id()
        self._init_test_dir()
        self._save_config()
        self._save_train_report()
        self._save_weights()

    def save_playing(self):
        self.mode = "play"
        self.init_time = self.config["init_time"]
        self._init_dir(self.assets_dir)
        self._init_dir(self.saves_dir)
        self.id = self._get_id()
        self._init_test_dir()
        self._save_config()
        self._save_play_report()

    def _get_id(self):
        """If an id file is available in assets_dir use that, otherwise get a new id."""
        idfile = "{}/id".format(self.assets_dir)
        if path.isfile(idfile):
            with open(idfile, "r") as file:
                id = file.read()
        else:
            id = self._get_new_id()
        return id

    def _get_new_id(self):
        """Get a new id for the test."""
        import uuid
        return uuid.uuid4()

    def _init_dir(self, dir):
        if not os.path.exists(os.path.abspath(dir)):
            os.makedirs(os.path.abspath(dir))

    def _init_test_dir(self):
        test = "{}/{}".format(self.saves_dir, self.id)
        self._init_dir(test)
        self.test_dir = test
        with open("{}/id".format(self.test_dir), "w+") as file:
            file.write("{}".format(self.id))

    def _save_config(self):
        config = self.config["config_file"]
        copyfile(config, "{}/{}/config_{}_{}_{}".format(self.saves_dir, self.id, self.mode, self.init_time,
                                                 os.path.basename(config)))

    def _save_weights(self):
        copyfile(self.last_name, "{}/{}".format(self.test_dir, os.path.basename(self.last_name)))

    def _save_train_report(self):
        scores = self.judge.scores
        mean = float(sum(scores)) / float(self.judge.mean_sample)
        self._save_report(mean)

    def _save_play_report(self):
        scores = self.judge.scores
        mean = float(sum(scores)) / float(len(scores))
        self._save_report(mean)

    def _save_report(self, mean):
        """Save a json file with all the relevant data about a test."""
        import datetime, json
        now = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        initial_time = self.config["init_time"]
        scores = self.judge.scores
        from git import Repo
        hexsha = Repo(search_parent_directories=True).head.object.hexsha
        report = {
            "a_comment": "",
            "test_start_date": initial_time,
            "test_end_date": now,
            "configs": self.config,
            "games": len(scores),
            "average_score": mean,
            "test_id": "{}".format(self.id),
            "git_hexsha": hexsha
        }
        if self.config["save_score"]:
            report["zzz_scores"] = scores
        if self.config["save_mean"]:
            report["zzz_means"] = self.judge.means
        with open("{}/report_{}_{}.json".format(self.test_dir, self.mode, self.init_time, now), "w+") as file:
            json.dump(report, file, indent=4, sort_keys=True)

    def update_tmp_weights(self):
        self._delete_old_tmp_weights()
        self._save_tmp_weights()

    def _save_tmp_weights(self):
        initial_time = self.config["init_time"]
        self.last_name = "{}/weights_{}_mean{}.h5".format(self.assets_dir, initial_time, self.judge.mean)
        self.judge.agent.model.save_weights(self.last_name, overwrite=False)

    def _delete_old_tmp_weights(self):
        if path.isfile(self.last_name):
            remove(self.last_name)

    def manual_stop_required(self):
        """Return true if a file named stop is present in assets_dir."""
        stopfile = "{}/stop".format(self.assets_dir)
        if path.isfile(stopfile):
            remove(stopfile)
            return True
        return False


class MultiSaveManager(SaveManager):
    """A SaveManager that supports multimodels."""

    def _save_tmp_weights(self):
        initial_time = self.config["init_time"]
        self.tmp_dir = "{}/tmp_weights_{}".format(self.assets_dir, initial_time)
        self._init_dir(self.tmp_dir)
        for situation in self.judge.agent.SM.situations:
            name = "{}".format(situation.name)
            filename = "{}/{}_weights.h5".format(self.tmp_dir, name)
            situation.situational_agent.model.save_weights(filename, overwrite=False)

    def _delete_old_tmp_weights(self):
        if hasattr(self, "tmp_dir"):
            if os.path.exists(os.path.abspath(self.tmp_dir)):
                import shutil
                shutil.rmtree(os.path.abspath(self.tmp_dir))

    def _save_weights(self):
        for root, dirs, files in os.walk(self.tmp_dir):
            for f in files:
                copyfile(os.path.join(root, f), os.path.join(self.test_dir, f))
