#Copyright (C) 2017 Andrea Asperti, Carlo De Pieri, Gianmaria Pedrini
#
#This file is part of Rogueinabox.
#
#Rogueinabox is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Rogueinabox is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

all: install

install: pydeps submodules-install build-rogue

update: submodules-update build-rogue

pydeps:
	( \
		pip install --upgrade pip; \
		pip install --upgrade setuptools; \
		pip install -r requirements.txt; \
	)

submodules-install:
	git submodule update --init --recursive

submodules-update:
	git submodule update --remote --recursive

build-rogue:
	( \
		cd rogue; \
		make; \
		cd ..; \
	)
