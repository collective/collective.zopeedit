#!/usr/bin/env python
# -*- coding: utf-8 -*-
###########################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# Copyright (c) 2005-2010 Thierry Benita - atReal <contact@atreal.net>
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
###########################################################################
"""Zope External Editor Helper Application
http://plone.org/products/zope-externaleditor-client"""
APP_NAME = "zopeedit"

from ConfigParser import ConfigParser
from hashlib import md5
from hashlib import sha1
from httplib import FakeSocket
from httplib import HTTPConnection
from httplib import HTTPSConnection
from subprocess import call
from subprocess import Popen
from sys import platform
from sys import version_info
from tempfile import mktemp
from time import sleep
from urllib2 import getproxies
from urllib2 import parse_http_list
from urllib2 import parse_keqv_list
from urlparse import urlparse

import base64
import gettext
import glob
import locale
import logging
import os
import re
import rfc822
import shutil
import socket
import ssl
import subprocess
import sys
import time
import traceback
import urllib


# get the path of zopeedit.py
try:
    # try to get the python file path
    system_path = os.path.split(__file__)[0]
except NameError:
    system_path = os.path.realpath(os.path.dirname(sys.argv[0]))

__version__ = '1.1.2'

# Where am i ?
# The windows version is used with py2exe and a python 2.x (actually 2.6)
# So the possibilities are:
#   - under windows with a python 2.x
#   - under Linux/unix with python 2.x (>= 2.6 is assumed) or python 3.x


py3 = version_info[0] == 3

win32 = sys.platform == "win32"
osx = sys.platform == "darwin"
linux = sys.platform == "linux2"

# Windows specifics
if win32:
    from os import startfile

    # import pywin32 stuff first so it never looks into system32
    import pythoncom, pywintypes

    # prevent warnings from being turned into errors by py2exe
    import warnings

    warnings.filterwarnings("ignore")

# Mac OSX specifics
if osx:
    # Launch Services binding
    # find the application needed for a file and open the file into it
    from LaunchServices import LSOpenFSRef


## gettext start init
# Retrieve full path
local_path = os.path.join(system_path, "locales")

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

logger = logging.getLogger("zopeedit")
log_file = None

# Retrieve locale from system
lc, encoding = locale.getdefaultlocale()
if lc is None:
    lc = "en_EN"
    encoding = "UTF-8"

# Should work without that but it seems to be here most of time
gettext.bindtextdomain(APP_NAME, local_path)
gettext.textdomain(APP_NAME)

# Initialization of translations
lang = gettext.translation(APP_NAME, local_path, languages=[lc], fallback=True)
# fallback = true avoids to raise an IOError Exception
# when APP_NAME is not found.
_ = lang.lgettext
# __builtins__._ = _
## gettext end init


class Configuration:
    def __init__(self, path):
        # Create/read config file on instantiation
        self.path = path
        if not os.path.exists(path):
            f = open(path, "w")
            f.write(default_configuration)
            f.close()
        self.config = ConfigParser()
        self.config.readfp(open(path))
        logger.info("init at: %s" % time.asctime(time.localtime()))
        logger.info("local_path: %r" % local_path)

    def save(self):
        """Save config options to disk"""
        self.config.write(open(self.path, "w"))
        logger.info("save at: %s" % time.asctime(time.localtime()))

    def set(self, section, option, value):
        self.config.set(section, option, value)

    def __getattr__(self, name):
        # Delegate to the ConfigParser instance
        return getattr(self.config, name)

    def getAllOptions(self, meta_type, content_type, title, extension, host_domain):
        """Return a dict of all applicable options for the
           given meta_type, content_type and host_domain
        """
        opt = {}
        sep = content_type.find("/")
        general_type = "%s/*" % content_type[:sep]

        # Divide up the domains segments and create a
        # list of domains from the bottom up
        host_domain = host_domain.split(".")
        domains = []
        for i in range(len(host_domain)):
            domains.append("domain:%s" % ".".join(host_domain[i:]))
        domains.reverse()

        sections = ["general"]
        sections.extend(domains)
        sections.append("meta-type:%s" % meta_type)
        sections.append("general-type:%s" % general_type)
        sections.append("content-type:%s" % content_type)
        sections.append("title:%s" % title)

        for section in sections:
            if self.config.has_section(section):
                for option in self.config.options(section):
                    opt[option] = self.config.get(section, option)
                    logger.debug("option %s: %s" % (option, opt[option]))

        # No extension and there is an extension in the metadata
        if opt.get("extension") is None and extension is not None:
            opt["extension"] = extension

        return opt


class NullResponse:
    """ Fake Response in case of http error
    """

    def getheader(self, n, d=None):
        return d

    def read(self):
        return "(No Response From Server)"


class ExternalEditor:
    """ ExternalEditor is the main class of zopeedit.
        It is in charge of making the link between the client editor
        and the server file object.
        There are 2 main actions :
        - launch('filename') : starts the edition process
        - editConfig() : allows the end user to edit a local options file
    """

    def __init__(self, input_file=""):
        """ arguments :
                - 'input_file' is the main file received from the server.
        """
        self.networkerror = False
        self.input_file = input_file
        # Setup logging.
        global log_file
        log_file = mktemp(suffix="-zopeedit-log.txt")
        # print(log_file)
        log_filehandler = logging.FileHandler(log_file)
        log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        log_filehandler.setFormatter(log_formatter)
        logger.addHandler(log_filehandler)
        logger.setLevel(logging.DEBUG)

        logger.info(
            _(
                "\n"
                "|-----------------------------------------------------------|\n"
                "|                                                           |\n"
                "| ZopeEdit version %s                                       |\n"
                "|                                                           |\n"
                "| This file is a log file.                                  |\n"
                "|                                                           |\n"
                "| Please save it and send it to your administrator.         |\n"
                "|                                                           |\n"
                "|-----------------------------------------------------------|\n"
                "| This version is maintained by atReal contact@atreal.net   |\n"
                "|-----------------------------------------------------------|\n"
                "\n\n\n\n"
            )
            % __version__
        )
        logger.info("Opening %r.", self.input_file)

        # If there is no filename, don't try to use it !
        if self.input_file == "":
            self.metadata = {}
            self.host = ""
            self.loadConfig()
            return

        try:
            # Open the input file and read the metadata headers
            in_f = open(self.input_file, "rb")
            m = rfc822.Message(in_f)

            self.metadata = m.dict.copy()

            # Special care for Dexterity Item content type, which
            # is encapsuled as its own rfc2822 message by plone.rfc822
            if self.metadata["meta_type"] == "Dexterity Item":
                import email, StringIO
                from email.header import decode_header
                msg = email.message_from_string(in_f.read())
                self.dexterity = dict(msg.items())
                encoded_title = self.dexterity.get(
                    "title", self.metadata.get("title", "")
                )
                self.metadata["title"] = decode_header(encoded_title)[0][0]
                self.metadata["content_type"] = self.dexterity.get(
                    "Content-Type", self.metadata.get("content_type", "text/plain")
                )
                in_f = StringIO.StringIO()
                in_f.write(msg.get_payload(decode=True))
                in_f.seek(0)

            logger.debug("metadata: %s" % repr(self.metadata))

            # Parse the incoming url
            scheme, self.host, self.path = urlparse(self.metadata["url"])[:3]

            # Keep the full url for proxy
            self.url = self.metadata["url"]
            self.ssl = scheme == "https"

            # initialyze configuration based on the config file and default values
            self.loadConfig()

            # Get last-modified
            last_modified = None
            if self.metadata.has_key("last-modified"):
                last_modified = self.metadata["last-modified"]
                self.last_modified = http_date_to_datetime(last_modified)
                logger.debug("last_modified: %s" % str(self.last_modified))

            # Retrieve original title
            self.title = (
                self.metadata["title"]
                .decode(self.server_charset)
                .encode(self.client_charset, "ignore")
            )

            # Write the body of the input file to a separate file
            if self.long_file_name:
                sep = self.options.get("file_name_separator", ",")
                content_file = urllib.unquote("-%s%s" % (self.host, self.path))
                content_file = (
                    content_file.replace("/", sep).replace(":", sep).replace(" ", "_")
                )
            else:
                content_file = "-" + urllib.unquote(self.path.split("/")[-1]).replace(
                    " ", "_"
                )

            extension = self.options.get("extension")
            if extension and not content_file.endswith(extension):
                content_file = content_file + extension
            if self.options.has_key("temp_dir"):
                while 1:
                    temp = os.path.expanduser(self.options["temp_dir"])
                    temp = os.tempnam(temp)
                    content_file = "%s%s" % (temp, content_file)
                    if not os.path.exists(content_file):
                        break
            else:
                content_file = mktemp(content_file, "rw")

            logger.debug("Destination filename will be: %r.", content_file)

            body_f = open(content_file, "wb")
            shutil.copyfileobj(in_f, body_f)
            self.content_file = content_file
            self.saved = False
            body_f.close()
            in_f.close()

            # cleanup the input file if the clean_up option is active
            if self.clean_up:
                try:
                    logger.debug("Cleaning up %r.", self.input_file)
                    os.chmod(self.input_file, 0777)
                    os.remove(self.input_file)
                except OSError:
                    logger.exception("Failed to clean up %r.", self.input_file)
                    pass  # Sometimes we aren't allowed to delete it

            # See if ssl is available
            if self.ssl:
                try:
                    from socket import ssl
                except ImportError:
                    fatalError(
                        "SSL support is not available on this \
                                system.\n"
                        "Make sure openssl is installed "
                        "and reinstall Python."
                    )
            self.lock_token = None
            self.did_lock = False
        except:
            # for security, always delete the input file even if
            # a fatal error occurs, unless explicitly stated otherwise
            # in the config file
            if getattr(self, "clean_up", 1):
                try:
                    exc, exc_data = sys.exc_info()[:2]
                    os.remove(self.input_file)
                except OSError:
                    # Sometimes we aren't allowed to delete it
                    raise exc, exc_data
            raise

    def __del__(self):
        logger.info("ZopeEdit ends at: %s" % time.asctime(time.localtime()))

    def loadConfig(self):
        """ Read the configuration file and set default values """
        config_path = self.getConfigPath()
        self.config = Configuration(config_path)
        # Get all configuration options
        self.options = self.config.getAllOptions(
            self.metadata.get("meta_type", ""),
            self.metadata.get("content_type", ""),
            self.metadata.get("title", ""),
            self.metadata.get("extension"),
            self.host,
        )

        logger.info("loadConfig: all options : %r" % self.options)

        # Log level
        logger.setLevel(LOG_LEVELS[self.options.get("log_level", "info")])

        # Get autolauncher in case of an unknown file
        self.autolauncher = self.options.get(
            "autolauncher", "gnome-open;kde-open;xdg-open"
        )
        logger.debug("loadConfig: autolauncher: %r" % self.autolauncher)

        # Get default editors, in case none is found
        if win32:
            self.defaulteditors = self.options.get("defaulteditors", "notepad")
        else:
            self.defaulteditors = self.options.get(
                "defaulteditors", "gedit;kedit;gvim;vim;emacs;nano"
            )
        logger.debug("loadConfig: defaulteditors: %s" % self.defaulteditors)

        # Get autoproxy option : do we want to configure proxy from system ?
        self.autoproxy = self.options.get("autoproxy", "")
        logger.debug("loadConfig: autoproxy: %r" % self.autoproxy)

        # Get proxy from options
        self.proxy = self.options.get("proxy", "")
        proxies = getproxies()
        logger.debug("loadConfig: system proxies : %r" % proxies)
        if self.proxy == "" and self.autoproxy:
            if proxies.has_key("http"):
                self.proxy = proxies["http"]
        if self.proxy.startswith("http://"):
            self.proxy = self.proxy[7:]
        if self.proxy.find("/") > -1:
            self.proxy = self.proxy[: self.proxy.find("/")]
        logger.debug("loadConfig: Proxy set to : %s" % self.proxy)

        # Lock file name for editors that create a lock file
        self.lock_file_schemes = self.options.get(
            "lock_file_schemes", ".~lock.%s#;~%s.lock;.%s.swp"
        ).split(";")
        logger.debug("loadConfig: lock_files_schemes: %s" % self.lock_file_schemes)

        # Proxy user and pass
        self.proxy_user = self.options.get("proxy_user", "")
        logger.debug("loadConfig: proxy_user: %s" % self.proxy_user)
        self.proxy_pass = self.options.get("proxy_pass", "")
        logger.debug("loadConfig: proxy_pass: %s" % self.proxy_pass)

        # Create a new version when the file is closed ?
        self.version_control = int(self.options.get("version_control", 0))
        logger.debug("loadConfig: version_control: %s" % self.version_control)

        self.version_command = self.options.get("version_command", "/saveasnewversion")
        self.version_command += "?versioncomment=ZopeEdit%%20%s" % __version__
        logger.debug("loadConfig: version_command: %s" % self.version_command)

        # Should we keep the log file?
        self.keep_log = int(self.options.get("keep_log", 1))
        logger.debug("loadConfig: keep_log: %s" % self.keep_log)

        # Should we always borrow the lock when it does exist ?
        self.use_locks = int(self.options.get("use_locks", 1))
        logger.debug("loadConfig: use_locks: %s" % self.use_locks)
        self.always_borrow_locks = int(self.options.get("always_borrow_locks", 0))
        logger.debug("loadConfig: always_borrow_locks: %s" % self.always_borrow_locks)

        # Should we inform the user about lock issues ans allow him to edit the file ?
        self.manage_locks = int(self.options.get("manage_locks", 1))
        logger.debug("loadConfig: manage_locks: %s" % self.manage_locks)

        self.lock_timeout = self.options.get("lock_timeout", "86400")
        logger.debug("loadConfig: lock_timeout: %s" % self.lock_timeout)

        # Should we clean-up temporary files ?
        self.clean_up = int(self.options.get("cleanup_files", 1))
        logger.debug("loadConfig: cleanup_files: %s" % self.clean_up)

        self.save_interval = float(self.options.get("save_interval", 2))
        logger.debug("loadConfig: save_interval: %s" % self.save_interval)
        self.max_is_alive_counter = int(self.options.get("max_isalive_counter", 5))
        logger.debug("loadConfig: max_isalive_counter: %s" % self.max_is_alive_counter)

        # Server charset
        self.server_charset = self.options.get("server_charset", "utf-8")
        logger.debug("loadConfig: server_charset: %s" % self.server_charset)

        # Client charset
        self.client_charset = encoding
        logger.debug("loadConfig: client_charset: %s" % self.client_charset)

        # Do we use long file name ? If not we use a generated file name.
        self.long_file_name = int(self.options.get("long_file_name", 0))
        logger.debug("loadConfig: long_filename: %s" % self.long_file_name)

        # Editors for the current content type
        self.editor = self.options.get("editor")
        if self.editor is not None:
            self.editor = self.findAvailableEditor(self.editor)
        logger.debug("loadConfig: editor: %s" % self.editor)

    def findAvailableEditor(self, editors_list):
        """ Find an available editor (Linux only)
        """
        if not linux:
            return editors_list

        editors = editors_list.split(";")

        for editor in editors:
            for path in os.environ["PATH"].split(":"):
                if editor in os.listdir(path):
                    return editor
        # no editor found
        return None

    def getConfigPath(self, force_local_config=False):
        """ Retrieve the configuration path
            It may be local if there is a user configuration file
            or global for all users
        """
        if win32:
            # Get Application Data
            app_data = os.environ["APPDATA"]
            # Create application folder in Application Data if it isn't here
            if not os.path.isdir(
                os.path.expanduser(os.path.join(app_data, "collective.zopeedit"))
            ):
                os.makedirs(
                    os.path.expanduser(os.path.join(app_data, "collective.zopeedit"))
                )
            # Check the AppData first and then the program dir
            config_path = os.path.expanduser(
                os.path.join(app_data, "collective.zopeedit", "ZopeEdit.ini")
            )

            # sys.path[0] might be library.zip!!!!
            app_dir = sys.path[0]
            if app_dir.lower().endswith("library.zip"):
                app_dir = os.path.dirname(app_dir)
            global_config = os.path.join(app_dir or "", "ZopeEdit.ini")

            if not force_local_config and not os.path.exists(config_path):
                logger.info(
                    "getConfigPath: Config file %r does not exist. "
                    "Using global configuration file: %r.",
                    config_path,
                    global_config,
                )

                # Don't check for the existence of the global
                # config file. It will be created anyway.
                config_path = global_config

        elif osx:
            config_path = os.path.expanduser("~/ZopeEdit.ini")

        else:
            # make config file using freedesktop config folders
            if not os.path.isdir(os.path.expanduser("~/.config/collective.zopeedit")):
                os.makedirs(os.path.expanduser("~/.config/collective.zopeedit"))
            config_path = os.path.expanduser(
                "~/.config/collective.zopeedit/ZopeEdit.ini"
            )

        logger.info("getConfigPath: Using user configuration file: %r.", config_path)
        return config_path

    def cleanContentFile(self, tried_cleanup=False):
        if self.clean_up and hasattr(self, "content_file"):
            # for security we always delete the files by default
            try:
                os.remove(self.content_file)
                logger.info(
                    "Content File cleaned up %r at %s"
                    % (self.content_file, time.asctime(time.localtime()))
                )
                return True
            except OSError:
                if tried_cleanup:
                    logger.exception(
                        "Failed to clean up %r at %s"
                        % (self.content_file, time.asctime(time.localtime()))
                    )
                    # Issue logged, but it's already the second try.
                    # So continue.
                    return False
                else:
                    logger.debug(
                        "Failed to clean up %r at %s ;\
                                  retry in 10 sec"
                        % (self.content_file, time.asctime(time.localtime()))
                    )

                    # Some editors close first and save the file ;
                    # This may last few seconds
                    time.sleep(10)

                    # This is the first try. It may be an editor issue.
                    # Let's retry later.
                    return self.cleanContentFile(tried_cleanup=True)

    def getEditorCommand(self):
        """ Return the editor command
        """
        editor = self.editor

        if win32 and editor is None:
            from _winreg import HKEY_CLASSES_ROOT, OpenKeyEx, QueryValueEx, EnumKey
            from win32api import FindExecutable, ExpandEnvironmentStrings

            # Find editor application based on mime type and extension
            content_type = self.metadata.get("content_type")
            extension = self.options.get("extension")

            logger.debug(
                "Have content type: %r, extension: %r", content_type, extension
            )
            if content_type:
                # Search registry for the extension by MIME type
                try:
                    key = "MIME\\Database\\Content Type\\%s" % content_type
                    key = OpenKeyEx(HKEY_CLASSES_ROOT, key)
                    extension, nil = QueryValueEx(key, "Extension")
                    logger.debug(
                        "Registry has extension %r for " "content type %r",
                        extension,
                        content_type,
                    )
                except EnvironmentError:
                    pass

            if extension is None and self.metadata.has_key("url"):
                url = self.metadata["url"]
                dot = url.rfind(".")

                if dot != -1 and dot > url.rfind("/"):
                    extension = url[dot:]
                    logger.debug("Extracted extension from url: %r", extension)
            classname = editor = None
            if extension is not None:
                try:
                    key = OpenKeyEx(HKEY_CLASSES_ROOT, extension)
                    classname, nil = QueryValueEx(key, None)
                    logger.debug(
                        "ClassName for extension %r is: %r", extension, classname
                    )
                except EnvironmentError:
                    classname = None

            if classname is not None:
                try:
                    # Look for Edit action in registry
                    key = OpenKeyEx(
                        HKEY_CLASSES_ROOT, classname + "\\Shell\\Edit\\Command"
                    )
                    editor, nil = QueryValueEx(key, None)
                    logger.debug("Edit action for %r is: %r", classname, editor)
                except EnvironmentError:
                    pass

            if classname is not None and editor is None:
                logger.debug(
                    "Could not find Edit action for %r. " "Brute-force enumeration.",
                    classname,
                )
                # Enumerate the actions looking for one
                # starting with 'Edit'
                try:
                    key = OpenKeyEx(HKEY_CLASSES_ROOT, classname + "\\Shell")
                    index = 0
                    while 1:
                        try:
                            subkey = EnumKey(key, index)
                            index += 1
                            if str(subkey).lower().startswith("edit"):
                                subkey = OpenKeyEx(key, subkey + "\\Command")
                                editor, nil = QueryValueEx(subkey, None)
                            if editor is None:
                                continue
                            logger.debug(
                                "Found action %r for %r. " "Command will be: %r",
                                subkey,
                                classname,
                                editor,
                            )
                        except EnvironmentError:
                            break
                except EnvironmentError:
                    pass

            if classname is not None and editor is None:
                try:
                    # Look for Open action in registry
                    key = OpenKeyEx(
                        HKEY_CLASSES_ROOT, classname + "\\Shell\\Open\\Command"
                    )
                    editor, nil = QueryValueEx(key, None)
                    logger.debug(
                        "Open action for %r has command: %r. ", classname, editor
                    )
                except EnvironmentError:
                    pass

            if editor is None:
                try:
                    nil, editor = FindExecutable(self.content_file, "")
                    logger.debug(
                        "Executable for %r is: %r. ", self.content_file, editor
                    )
                except pywintypes.error:
                    pass

            # Don't use IE as an "editor"
            if editor is not None and editor.find("\\iexplore.exe") != -1:
                logger.debug("Found iexplore.exe. Skipping.")
                editor = None

            if editor is not None:
                return ExpandEnvironmentStrings(editor)

        elif editor is None and osx:
            # we will use the system in order to find the editor
            pass

        elif editor is None:
            # linux
            logger.debug("getEditorCommand: editor is None and linux")
            logger.debug("getEditorCommand: self.autolauncher = %s" % self.autolauncher)
            editor = self.findAvailableEditor(self.autolauncher)
            logger.debug("getEditorCommand: editor is : %s" % editor)

        return editor

    def launch(self):
        """ Launch external editor
        """

        # Do we have an input file ?
        if self.input_file == "":
            fatalError(_("No input file. \n" "ZopeEdit will close."), exit=0)

        self.last_mtime = os.path.getmtime(self.content_file)
        self.initial_mtime = self.last_mtime
        self.last_saved_mtime = self.last_mtime
        self.dirty_file = False

        command = self.getEditorCommand()

        # lock before opening the file in the editor
        if not self.lock():
            self.networkerror = True
            msg = (
                _(
                    "%s\n"
                    "Unable to lock the file on the server.\n"
                    "This may be a network or proxy issue.\n"
                    "Your log file will be opened\n"
                    "Please save it and send it to your administrator."
                )
                % self.title
            )
            errorDialog(msg)
            logger.error("launch: lock failed. Exit.")
            self.editFile(log_file, detach=True, default=True)
            sys.exit()

        # Extract the executable name from the command
        if command and win32:
            if command.find("\\") != -1:
                bin = re.search(r"\\([^\.\\]+)\.exe", command.lower())
                if bin is not None:
                    bin = bin.group(1)
            else:
                bin = command.lower().strip()
        else:
            bin = command

        logger.info("launch: Command %r, will use %r", command, bin)

        if bin is not None:
            # Try to load the plugin for this editor
            try:
                logger.debug(
                    "launch: bin is not None - try to load a plugin : %s" % bin
                )
                module = "Plugins.%s" % bin
                Plugin = __import__(module, globals(), locals(), ("EditorProcess",))
                self.editor = Plugin.EditorProcess(self.content_file)
                logger.info(
                    "launch: Launching Plugin %r with: %r", Plugin, self.content_file
                )
            except (ImportError, AttributeError):
                logger.debug("launch: Error while to load the plugin ; set bin to None")
                bin = None

        if bin is None:
            logger.info("launch: No plugin found ; using standard editor process")
            # Use the standard EditorProcess class for this editor
            if win32:
                file_insert = "%1"
            else:
                file_insert = "$1"

            if command.find(file_insert) > -1:
                command = command.replace(file_insert, self.content_file)
            else:
                command = "%s %s" % (command, self.content_file)

            logger.info("launch: Launching EditorProcess with: %r", command)
            self.editor = EditorProcess(
                command,
                self.content_file,
                self.max_is_alive_counter,
                self.lock_file_schemes,
            )
            logger.info("launch: Editor launched successfully")

        launch_success = self.editor.isAlive()
        if not launch_success:
            fatalError(_("Unable to edit your file.\n\n" "%s") % command)

        file_monitor_exit_state = self.monitorFile()

        unlock_success = self.unlock()
        if not unlock_success:
            logger.error("launch: not unlock_success. Flag networkerror")
            self.networkerror = True

        # Check is a file has been modified but not saved back to zope

        # Clean content file
        if self.dirty_file:
            logger.exception(
                "launch: Some modifications are NOT saved "
                "we'll re-open file and logs"
            )

            self.clean_up = False
            self.keep_log = True
        elif (not unlock_success) and self.clean_up:
            logger.exception("launch: Unlock failed and we have to clean up files")
            self.clean_up = False
            self.keep_log = True

        if self.networkerror or self.dirty_file:
            if self.dirty_file:
                # Reopen file when there is an issue...
                errorDialog(
                    _(
                        "Network error :\n"
                        "Your working copy will be re-opened,\n"
                        "\n"
                        "SAVE YOUR WORK ON YOUR DESKTOP.\n"
                        "\n"
                        "A log file will be opened\n"
                        "Please save it and send it to your administrator."
                    )
                )
                self.editor.startEditor()
            else:
                errorDialog(
                    _(
                        "Network error : your file is still locked.\n"
                        "\n"
                        "A log file will be opened\n"
                        "Please save it and send it to your administrator."
                    )
                )
            self.editFile(log_file, detach=True, default=True)
            sys.exit(0)

        # Inform the user of what has been done when the edition is finished
        # without issue
        if (
            file_monitor_exit_state == "closed modified"
            or file_monitor_exit_state == "manual close modified"
        ):
            msg = _(
                "%(title)s\n\n"
                "File : %(content_file)s\n\n"
                "Saved at : %(time)s\n\n"
                "Edition completed"
            ) % {
                "title": self.title,
                "content_file": self.content_file,
                "time": time.ctime(self.last_saved_mtime),
            }
            messageDialog(msg)
        elif (
            file_monitor_exit_state == "closed not modified"
            or file_monitor_exit_state == "manual close not modified"
        ):
            msg = _("%(title)s\n\n" "Edition completed") % {
                "title": self.title,
            }
            messageDialog(msg)

        self.cleanContentFile()

    def monitorFile(self):
        """ Check if the file is edited and if it is modified.
        If it's modified save it back.
        If it is not any more edited exit with an information on what happened.
         -> was saved back
         -> was automatically detected
         -> was manually controled by the user
        """
        final_loop = False
        isAlive_detected = False
        returnChain = ""

        while 1:
            if not final_loop:
                self.editor.wait(self.save_interval)
            mtime = os.path.getmtime(self.content_file)

            if mtime != self.last_mtime:
                logger.debug("monitorFile: File is dirty : changes detected !")
                self.dirty_file = True
                launch_success = True
                if self.versionControl():
                    logger.info("monitorFile: New version created successfully")
                else:
                    logger.debug("monitorFile: No new version created")

                self.saved = self.putChanges()
                self.last_mtime = mtime
                if self.saved:
                    self.last_saved_mtime = mtime
                    self.dirty_file = False

            if not self.editor.isAlive():
                if final_loop:
                    # exit from monitorFile
                    logger.info("monitorFile: Final loop done; break")
                    return returnChain
                else:
                    # Check wether a file hasn't been saved before closing
                    if mtime != self.last_saved_mtime:
                        self.dirty_file = True
                        launch_success = True
                        self.saved = self.putChanges()
                        self.last_mtime = mtime
                        if self.saved:
                            self.last_saved_mtime = mtime
                            self.dirty_file = False
                    # Go through the loop one final time for good measure.
                    # Our editor's isAlive method may itself *block* during
                    # a save operation (seen in COM calls, which seem to
                    # respond asynchronously until they don't) and
                    # subsequently return false, but the editor may have
                    # actually saved the file to disk while the call
                    # blocked.  We want to catch any changes that happened
                    # during a blocking isAlive call.
                    if isAlive_detected:
                        if self.last_saved_mtime != self.initial_mtime:
                            logger.debug("monitorFile: closed modified")
                            returnChain = "closed modified"
                        else:
                            logger.debug("monitorFile: closed not modified")
                            returnChain = "closed not modified"
                    else:
                        if self.last_saved_mtime != self.initial_mtime:
                            msg = _(
                                "%(title)s\n\n"
                                "File : %(content_file)s\n"
                                "Saved at : %(time)s\n\n"
                                "Did you close your file ?"
                            ) % {
                                "title": self.title,
                                "content_file": self.content_file,
                                "time": time.ctime(self.last_saved_mtime),
                            }
                            if not askYesNo(msg):
                                logger.debug("monitorFile: manual continue modified")
                                continue
                            else:
                                logger.debug("monitorFile: manual closed modified")
                                returnChain = "manual close modified"

                        else:
                            msg = _("%(title)s :\n\n" "Did you close your file ?") % {
                                "title": self.title,
                            }
                            if not askYesNo(msg):
                                logger.debug(
                                    "monitorFile: manual continue not modified"
                                )
                                continue
                            else:
                                logger.debug("monitorFile: manual close not monified")
                                returnChain = "manual close not modified"
                    final_loop = True
                    logger.info("monitorFile: Final loop")
            else:
                isAlive_detected = True

    def putChanges(self):
        """Save changes to the file back to Zope"""
        logger.info("putChanges at: %s" % time.asctime(time.localtime()))

        f = open(self.content_file, "rb")
        body = f.read()
        logger.info("Document is %s bytes long" % len(body))
        f.close()
        headers = {"Content-Type": self.metadata.get("content_type", "text/plain")}

        if self.lock_token is not None:
            headers["If"] = "<%s> (<%s>)" % (self.path, self.lock_token)

        # Special care for Dexterity Item content type, which
        # is encapsuled as its own rfc2822 message by plone.rfc822
        if self.metadata["meta_type"] == "Dexterity Item":
            import email

            msg = email.message.Message()
            for key in self.dexterity:
                #  Including the id in the PUT message causes dexterity to
                #  rename the item, resulting in a lock error.
                if key == "id":
                    continue
                msg.add_header(key, self.dexterity[key])
            msg.set_payload(body)
            email.encoders.encode_base64(msg)
            body = str(msg)

        response = self.zopeRequest("PUT", headers, body)
        # Don't keep the body around longer than we need to
        del body

        if response.status / 100 != 2:
            # Something went wrong
            if self.manage_locks and askRetryAfterError(
                response,
                _(
                    "Network error\n"
                    "\n"
                    "Could not save the file to server.\n"
                    "\n"
                    "Error detail :\n"
                ),
            ):
                return self.putChanges()
            else:
                logger.error("Could not save to Zope\n" "Error during HTTP PUT")
                return False
        logger.info("File successfully saved back to the intranet")
        return True

    def lock(self):
        """Apply a webdav lock to the object in Zope
        usecases :
        - use_locks "1" and manage_locks "1"
            1 - no existing lock
                lock the file
                if error : ask user if retry or not
                if no retry and error : return False
            2 - existing lock
                if always_borrow_locks "yes"
                    borrow the lock and return True
                else ask user wether retrieve it or not
                    if not : exit with error
                    if yes : borrow the lock
        - use_locks "yes" and manage_locks "no"
            1 - no existing lock
                lock the file
                if error : exit with error
            2 - existing lock
                exit with error
        - use_locks "no"
            don't do anything and exit with no error
        """
        logger.debug("lock: lock at: %s" % time.asctime(time.localtime()))
        if not self.use_locks:
            logger.debug("lock: don't use locks")
            return True

        if self.metadata.get("lock-token"):
            # A lock token came down with the data, so the object is
            # already locked
            if not self.manage_locks:
                logger.critical(
                    "lock: object already locked : "
                    "lock tocken not empty\n "
                    "user doesn't manage locks, so... "
                    "exit"
                )
                msg = _("%s\n" "This object is already locked.") % (self.title)
                errorDialog(msg)
                sys.exit()
            # See if we can borrow the lock
            if self.always_borrow_locks or self.metadata.get("borrow_lock"):
                self.lock_token = "opaquelocktoken:%s" % self.metadata["lock-token"]
            else:
                msg = _(
                    "%s\n"
                    "This object is already locked by you "
                    "in another session.\n"
                    "Do you want to borrow this lock and continue ?"
                ) % (self.title)
                if askYesNo(msg):
                    self.lock_token = "opaquelocktoken:%s" % self.metadata["lock-token"]
                else:
                    logger.critical(
                        "lock: File locked and user doesn't want "
                        "to borrow the lock. Exit."
                    )
                    sys.exit()

        if self.lock_token is not None:
            logger.warning("lock: Existing lock borrowed.")
            return True

        # Create a new lock
        dav_lock_response = self.DAVLock()

        if dav_lock_response / 100 == 2:
            logger.info("lock: OK")
            self.did_lock = True
            return True

        # There was an error. Retry ?
        while self.manage_locks and not self.did_lock:
            dav_lock_response = self.DAVLock()

            if dav_lock_response / 100 == 2:
                logger.info("lock: OK")
                self.did_lock = True
                return True

            if dav_lock_response == 423:
                logger.warning("lock: object locked by someone else... " "EXIT !")
                msg = _("%s\n" "Object already locked") % (self.title)
                errorDialog(msg)
                exit()
            else:
                logger.error(
                    "lock: failed to lock object: "
                    "response status %s" % dav_lock_response
                )
                msg = _(
                    "%(title)s\n"
                    "Unable to get a lock on the server"
                    "(return value %(dav_lock_response)s)"
                ) % {"title": self.title, "dav_lock_response": dav_lock_response}

            msg += "\n"
            msg += _("Do you want to retry ?")
            if askRetryCancel(msg):
                logger.info("lock: Retry lock")
                continue
            else:
                logger.critical("lock: Unable to lock the file ; return False")
                logger.error("lock failed. Return False.")
                return False

    def DAVLock(self):
        """Do effectively lock the object"""
        logger.debug("DAVLock at: %s" % time.asctime(time.localtime()))

        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "Timeout": self.lock_timeout,
            "Depth": "0",
        }
        body = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<d:lockinfo xmlns:d="DAV:">\n'
            "  <d:lockscope><d:exclusive/></d:lockscope>\n"
            "  <d:locktype><d:write/></d:locktype>\n"
            "  <d:depth>infinity</d:depth>\n"
            "  <d:owner>\n"
            "  <d:href>Zope External Editor</d:href>\n"
            "  </d:owner>\n"
            "</d:lockinfo>"
        )

        response = self.zopeRequest("LOCK", headers, body)
        logger.debug("DAVLock response:%r" % response.status)
        dav_lock_response = response.status

        if dav_lock_response / 100 == 2:
            logger.info("Lock success.")
            # We got our lock, extract the lock token and return it
            reply = response.read()
            token_start = reply.find(">opaquelocktoken:")
            token_end = reply.find("<", token_start)
            if token_start > 0 and token_end > 0:
                self.lock_token = reply[token_start + 1 : token_end]

        return dav_lock_response

    def versionControl(self):
        """ If version_control is enabled, ZopeEdit will try to
            automatically create a new version of the file.
            The version is created only if the file is modified,
            just before the first save.
        """
        if not self.version_control:
            logger.debug(
                "versionControl: version_control is False : %s" % self.version_control
            )
            return False
        if self.saved:
            logger.debug("versionControl: don't create a version if " "already saved")
            return False
        response = self.zopeRequest("GET", command="%s" % self.version_command)
        logger.debug(
            "versionControl : " "return code of new version is %s" % response.status
        )
        if response.status == 302:
            return True
        else:
            logger.warning(
                "Creation of version failed : " "response status %s" % response.status
            )
            return False

    def unlock(self, interactive=True):
        """Remove webdav lock from edited zope object"""
        if not self.use_locks:
            logger.debug("unlock: use_locks is False " "return True.")
            return True

        if (not self.did_lock) and self.lock_token is None:
            return True  # nothing to do
        response = self.DAVunlock()
        status = int(response.status)
        logger.debug(
            "response : %s status : %s status/100: %s"
            % (response, status, status / 100)
        )
        while status / 100 != 2:
            # unlock failed
            logger.error(
                "Unlock failed at: %s did_lock=%s status=%s"
                % (time.asctime(time.localtime()), self.did_lock, status)
            )
            if askRetryAfterError(
                response,
                _("Network error\n" "\n" "Unable to unlock the file on server.\n"),
            ):
                status = self.DAVunlock().status
                continue
            else:
                return False
        logger.info("Unlock successfully. did_lock = %s" % self.did_lock)
        self.did_lock = False
        return True

    def DAVunlock(self):
        logger.debug("DAVunlock at: %s" % time.asctime(time.localtime()))
        headers = {"Lock-Token": self.lock_token}
        response = self.zopeRequest("UNLOCK", headers)
        logger.debug("DAVunlock response:%r" % response)
        return response

    def _get_authorization(self, host, method, selector, cookie, ssl, old_response):
        # get the challenge
        if ssl is True:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            h = HTTPSConnection(host, context=ctx)
        else:
            h = HTTPConnection(host)
        if cookie is not None:
            headers = {"Cookie": cookie}
        else:
            headers = {}
        h.request("HEAD", selector, headers=headers)
        r = h.getresponse()
        if r.status != 401:
            return None
        auth_header = r.getheader("www-authenticate").strip()
        if auth_header is None or not auth_header.lower().startswith("digest"):
            return None
        # XXX undocumented functions
        chal = parse_keqv_list(parse_http_list(auth_header[7:]))

        # get the user/password
        if self.identity is not None:
            username, password = self.identity
        else:
            # XXX undocumented functions
            username = parse_keqv_list(parse_http_list(old_response[7:]))["username"]
            password = askPassword(chal["realm"], username)
            self.identity = (username, password)

        # compute the authorization
        algorithm = chal.get("algorithm", "MD5")
        if algorithm == "MD5":
            H = lambda x: md5(x).hexdigest()
        elif algorithm == "SHA":
            H = lambda x: sha1(x).hexdigest()
        # XXX MD5-sess not implemented
        KD = lambda s, d: H("%s:%s" % (s, d))

        nonce = chal["nonce"]
        res = (
            'Digest username="%s", realm="%s", nonce="%s", '
            'algorithm="%s", '
            'uri="%s"' % (username, chal["realm"], nonce, chal["algorithm"], selector)
        )
        if "opaque" in chal:
            res += ', opaque="%s"' % chal["opaque"]

        A1 = "%s:%s:%s" % (username, chal["realm"], password)
        A2 = "%s:%s" % (method, selector)

        if "qop" in chal:
            # XXX auth-int not implemented
            qop = chal["qop"]
            nc = "00000001"
            cnonce = "12345678"
            res += ', qop="%s", nc="%s", cnonce="%s"' % (qop, nc, cnonce)

            response = KD(H(A1), "%s:%s:%s:%s:%s" % (nonce, nc, cnonce, qop, H(A2)))
        else:
            response = KD(H(A1), "%s:%s" % (nonce, H(A2)))

        res += ', response="%s"' % response
        return res

    def zopeRequest(self, method, headers={}, body="", command=""):
        """Send a request back to Zope"""
        logger.debug(
            "zopeRequest: method: %r, headers: %r, command: %r"
            % (method, headers, command)
        )
        if self.proxy == "":
            logger.debug(
                "zopeRequest: no proxy definition in config file : "
                "self.proxy is empty"
            )
            host = self.host
            url = self.path
            logger.debug(
                "zopeRequest: host:%s and url path:%r "
                "retrieved from system" % (host, url)
            )
        else:
            host = self.proxy
            url = self.url
            logger.debug(
                "zopeRequest: proxy defined in config file : "
                "host:%s url:%s" % (host, url)
            )
        url += command
        logger.debug("zopeRequest: url = %s" % url)
        logger.debug("zopeRequest: method = %s" % method)
        logger.debug("zopeRequest: command = %s" % command)
        try:
            if self.ssl and self.proxy:
                logger.debug("zopeRequest: ssl and proxy")
                # XXX
                # setup basic authentication
                proxy_host, proxy_port = self.proxy.split(":")
                proxy_port = int(proxy_port)
                logger.debug(
                    "zopeRequest: proxy_host; %r, proxy_port: %r"
                    % (proxy_host, proxy_port)
                )
                taburl = url.split("/")
                if len(taburl[2].split(":")) == 2:
                    port = int(taburl[2].split(":")[1])
                    host = taburl[2].split(":")[0]
                else:
                    if taburl[0] == "https:":
                        port = 443
                    else:
                        port = 80
                    host = taburl[2]

                proxy_authorization = ""
                if self.proxy_user and self.proxy_pass:
                    logger.debug(
                        "zopeRequest: proxy_user: %r, proxy_pass: XXX" % self.proxy_user
                    )
                    user_pass = base64.encodestring(
                        self.proxy_user + ":" + self.proxy_pass
                    )
                    proxy_authorization = (
                        "Proxy-authorization: Basic " + user_pass + "\r\n"
                    )

                proxy_connect = "CONNECT %s:%s HTTP/1.0\r\n" % (host, port)
                logger.debug("zopeRequest: proxy_connect: %r" % proxy_connect)
                user_agent = "User-Agent: Zope External Editor %s\r\n" % __version__
                proxy_pieces = proxy_connect + proxy_authorization + user_agent + "\r\n"
                # now connect, very simple recv and error checking
                logger.debug("zopeRequest: initialyze proxy socket")
                proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                logger.debug("zopeRequest: connect to proxy")
                proxy.connect((proxy_host, proxy_port))
                logger.debug(
                    "zopeRequest: send auth pieces to proxy (%r)" % proxy_pieces
                )
                proxy.sendall(proxy_pieces)
                logger.debug("zopeRequest: receive response fron proxy")
                response = proxy.recv(8192)
                status = response.split()[1]
                if status != str(200):
                    raise "Error status=", str(status)
                # trivial setup for ssl socket
                logger.debug("zopeRequest: wrap proxy to ssl")
                sock = ssl.wrap_socket(proxy)
                # initalize httplib and replace with your socket
                logger.debug("zopeRequest: initialyze HTTP connection")
                hc = HTTPConnection(proxy_host, proxy_port)
                hc.set_debuglevel(9)
                hc.sock = sock
                logger.debug(
                    "zopeRequest: putrequest method: %r, url: %r" % (method, url)
                )
                hc.putrequest(method, url)
                hc.putheader("User-Agent", "Zope External Editor/%s" % __version__)
                # hc.putheader('Connection', 'close')
                for header, value in headers.items():
                    hc.putheader(header, value)
                hc.putheader("Content-Length", str(len(body)))
                if self.metadata.get("auth", "").lower().startswith("basic"):
                    hc.putheader("Authorization", self.metadata["auth"])
                if self.metadata.get("cookie"):
                    hc.putheader("Cookie", self.metadata["cookie"])

                hc.endheaders()
                hc.send(body)
                response = hc.getresponse()
                logger.debug("zopeRequest: response: %r" % response)
                return response

            if self.ssl and not self.proxy:
                logger.debug("zopeRequest: ssl and no proxy")
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                h = HTTPSConnection(host, context=ctx)
            else:
                logger.debug("zopeRequest: no ssl and no proxy")
                h = HTTPConnection(host)

            h.putrequest(method, url)
            h.putheader("User-Agent", "Zope External Editor/%s" % __version__)
            for header, value in headers.items():
                h.putheader(header, value)
            h.putheader("Content-Length", str(len(body)))
            # authentification
            auth_header = self.metadata.get("auth", "")
            if auth_header.lower().startswith("basic"):
                h.putheader("Authorization", self.metadata["auth"])
            if auth_header.lower().startswith("digest"):
                authorization = self._get_authorization(
                    host, method, url, self.metadata.get("cookie"), False, auth_header
                )
                if authorization is not None:
                    h.putheader("Authorization", authorization)
            # cookie
            if self.metadata.get("cookie"):
                h.putheader("Cookie", self.metadata["cookie"])

            h.endheaders()
            h.send(body)
            response = h.getresponse()
            logger.debug("zopeRequest: response: %r" % response.status)
            return response
        except:
            # On error return a null response with error info
            logger.error("zopeRequest: we got an exception !")

            response = NullResponse()
            response.reason = sys.exc_info()[1]

            try:
                response.status, response.reason = response.reason
            except ValueError:
                response.status = 0

            if response.reason == "EOF occurred in violation of protocol":
                # Ignore this protocol error as a workaround for
                # broken ssl server implementations
                response.status = 200

            return response

    def editConfig(self):
        logger.info("Edit local configuration")
        user_config = self.getConfigPath(force_local_config=True)
        # Read the configuration file
        if win32:
            # Check the home dir first and then the program dir
            # sys.path[0] might be library.zip!!!!
            app_dir = sys.path[0]
            if app_dir.lower().endswith("library.zip"):
                app_dir = os.path.dirname(app_dir)
            global_config = os.path.join(app_dir or "", "ZopeEdit.ini")

            create_config_file = False
            if not os.path.exists(user_config):
                logger.info(
                    "Local configuration file %r does not exist. "
                    "Global configuration file is : %r.",
                    user_config,
                    global_config,
                )
                create_config_file = True
            else:
                if askYesNo(_("Reset configuration file ?")):
                    create_config_file = True
                    logger.info(
                        "Replace the configuration file " "with the default one."
                    )
            if create_config_file:
                input_config_file = open(global_config, "r")
                output_config_file = open(user_config, "w")
                for l in input_config_file.readlines():
                    output_config_file.write(l)
                input_config_file.close()
                output_config_file.close()

        else:
            if askYesNo(
                _(
                    "Do you want to replace your "
                    "configuration file \n"
                    "with the default one ?"
                )
            ):
                logger.info("Replace the configuration file with " "the default one.")
                output_config = open(user_config, "w")
                output_config.write(default_configuration)
                output_config.close()
        self.editFile(user_config, default=True)

    def editFile(self, file, detach=False, default=False):
        # launch default editor with the user configuration file
        if default:
            editor = self.findAvailableEditor(self.defaulteditors)
        else:
            editor = self.getEditorCommand()
        if not editor:
            if osx:
                LSOpenFSRef(file, None)
            else:
                logger.critical("editFile: No editor found. " "File edition failed.")
        logger.info("editFile: Edit file %s with editor %s" % (file, editor))

        p = Popen("%s %s" % (editor, file), shell=True)
        if linux:
            if detach:
                p.poll()
            else:
                sts = os.waitpid(p.pid, 0)[1]
                logger.debug("sts : %s" % sts)
            if p.pid == 0:
                logger.debug(
                    "editFile: error with the detected editor ; "
                    "try with a default one as last option"
                )
                editor = self.findAvailableEditor(self.defaulteditors)
                logger.info("editFile: Edit file %s with editor %s" % (file, editor))
                logger.debug(
                    "editFile: launching editor in a shell environment : %s %s"
                    % (editor, file)
                )
                p = Popen("%s %s" % (editor, file), shell=True)
                if linux:
                    if detach:
                        p.poll()
                    else:
                        sts = os.waitpid(p.pid, 0)[1]
                        logger.debug("sts : %s" % sts)


title = "Zope External Editor"


def askRetryAfterError(response, operation, message=""):
    """Dumps response data"""
    if not message and response.getheader("Bobo-Exception-Type") is not None:
        message = "%s: %s" % (
            response.getheader("Bobo-Exception-Type"),
            response.getheader("Bobo-Exception-Value"),
        )
    return askRetryCancel(
        '%s\n"%d %s - %s"' % (operation, response.status, response.reason, message)
    )


class EditorProcess:
    def __init__(self, command, contentfile, max_is_alive_counter, lock_file_schemes):
        """Launch editor process"""
        # Prepare the command arguments, we use this regex to
        # split on whitespace and properly handle quoting
        self.command = command
        self.contentfile = contentfile
        self.max_is_alive_counter = max_is_alive_counter
        self.lock_file_schemes = lock_file_schemes
        self.arg_re = r"""\s*([^'"]\S+)\s+|\s*"([^"]+)"\s*|\s*'([^']+)'\s*"""
        self.is_alive_by_file = None
        # do we check file or pid ?
        self.is_alive_counter = 0  # number of isAlive Cycles
        self.starting = True  # still in a starting cycle
        if win32:
            self.methods = {
                1: self.isFileLockedByLockFile,
                2: self.isFileOpenWin32,
                3: self.isPidUpWin32,
            }
            self.nb_methods = 3
        elif osx:
            self.methods = {1: self.isFileLockedByLockFile, 2: self.isFileOpen}
            self.nb_methods = 2
        else:
            self.methods = {
                1: self.isFileLockedByLockFile,
                2: self.isFileOpen,
                3: self.isPidUp,
            }
            self.nb_methods = 3
        self.lock_detected = False
        self.selected_method = False

        if win32:
            self.startEditorWin32()
        elif osx:
            self.startEditorOsx()
        else:
            self.startEditor()

    def startEditorWin32(self):
        try:
            logger.debug("CreateProcess: %r", self.command)
            self.handle, nil, nil, nil = CreateProcess(
                None, self.command, None, None, 1, 0, None, None, STARTUPINFO()
            )
        except pywintypes.error, e:
            fatalError(
                "Error launching editor process\n" "(%s):\n%s" % (self.command, e[2])
            )

    def startEditorOsx(self):
        res = LSOpenFSRef(self.contentfile, None)

    def startEditor(self):
        args = re.split(self.arg_re, self.command.strip())
        args = filter(None, args)  # Remove empty elements
        logger.debug("starting editor %r" % args)
        self.pid = Popen(args).pid
        logger.debug("Pid is %s" % self.pid)

    def wait(self, timeout):
        """Wait for editor to exit or until timeout"""
        sleep(timeout)

    def isFileOpenWin32(self):
        try:
            fileOpen = file(self.contentfile, "a")
        except IOError, e:
            if e.args[0] == 13:
                logger.debug("Document is writeLocked by command")
                self.cmdLocksWrite = True
                return True
            else:
                logger.error("%s %s " % (e.__class__.__name__, str(e)))
        fileOpen.close()
        logger.info("File is not open : Editor is closed")
        return False

    def isPidUpWin32(self):
        if GetExitCodeProcess(self.handle) == 259:
            logger.info("Pid is up : Editor is still running")
            return True
        logger.info("Pid is not up : Editor exited")
        return False

    def isFileOpen(self):
        """Test if File is locked (filesystem)"""
        logger.debug("test if the file edited is locked by filesystem")
        command = "/bin/fuser"
        if not os.path.exists(command):
            command = "/usr/bin/fuser"

        process = Popen([command, self.command.split(" ")[-1]], stdout=subprocess.PIPE)
        process.wait()
        fileOpenWith = process.stdout.read()
        return fileOpenWith != ""

    def isPidUp(self):
        """Test PID"""
        logger.debug("test if PID is up")
        try:
            exit_pid, exit_status = os.waitpid(self.pid, os.WNOHANG)
        except OSError:
            return False
        return exit_pid != self.pid

    def isFileLockedByLockFile(self):
        """Test Lock File (extra file)"""
        if win32:
            file_separator = "\\"
        else:
            file_separator = "/"
        original_filepath = self.contentfile.split(file_separator)
        logger.debug("log file schemes : %s" % self.lock_file_schemes)

        for i in self.lock_file_schemes:
            filepath = original_filepath[:]
            if i == "":
                continue
            filepath[-1] = i % filepath[-1]
            filename = file_separator.join(filepath)
            logger.debug("Test: lock file : %s" % filename)
            if glob.glob(filename):
                self.lock_file_schemes = [i]
                return True
        return False

    def isAlive(self):
        """Returns true if the editor process is still alive
           is_alive_by_file stores whether we check file or pid
           file check has priority"""

        if self.starting:
            logger.info(
                "isAlive : still starting. Counter : %s" % self.is_alive_counter
            )
            if self.is_alive_counter < self.max_is_alive_counter:
                self.is_alive_counter += 1
            else:
                self.starting = False
        for i in range(1, self.nb_methods + 1):
            if self.methods[i]():
                logger.debug("isAlive: True( %s : %s)" % (i, self.methods[i].__doc__))
                if i != self.selected_method:
                    logger.info(
                        "DETECTION METHOD CHANGE : "
                        "Level %s - %s" % (i, self.methods[i].__doc__)
                    )
                self.selected_method = i
                self.nb_methods = i
                self.lock_detected = True
                return True
        logger.info("isAlive : no edition detected.")
        if self.starting and not self.lock_detected:
            logger.debug("isAlive : still in the startup process :" "continue.")
            return True
        return False


## Platform specific declarations ##

if win32:
    import Plugins  # Assert dependancy
    from win32ui import MessageBox
    from win32process import CreateProcess, GetExitCodeProcess, STARTUPINFO
    from win32event import WaitForSingleObject
    from win32con import (
        MB_OK,
        MB_OKCANCEL,
        MB_YESNO,
        MB_RETRYCANCEL,
        MB_SYSTEMMODAL,
        MB_ICONERROR,
        MB_ICONQUESTION,
        MB_ICONEXCLAMATION,
    )

    def errorDialog(message):
        MessageBox(message, title, MB_OK + MB_ICONERROR + MB_SYSTEMMODAL)

    def messageDialog(message):
        MessageBox(message, title, MB_OK + MB_ICONEXCLAMATION + MB_SYSTEMMODAL)

    def askRetryCancel(message):
        return (
            MessageBox(
                message,
                title,
                MB_OK + MB_RETRYCANCEL + MB_ICONEXCLAMATION + MB_SYSTEMMODAL,
            )
            == 4
        )

    def askYesNo(message):
        return (
            MessageBox(
                message, title, MB_OK + MB_YESNO + MB_ICONQUESTION + MB_SYSTEMMODAL
            )
            == 6
        )

    def askPassword(realm, username):
        import pywin.dialogs.login

        title = _("Please enter your password")
        userid, password = pywin.dialogs.login.GetLogin(title, username)
        return password


else:  # Posix platform
    from time import sleep
    import re

    def has_tk():
        """Sets up a suitable tk root window if one has not
           already been setup. Returns true if tk is happy,
           false if tk throws an error (like its not available)"""
        # create a hidden root window to make Tk happy
        if not locals().has_key("tk_root"):
            try:
                global tk_root
                from Tkinter import Tk

                tk_root = Tk()
                tk_root.withdraw()
                return True
            except:
                return False
        return True

    def tk_flush():
        tk_root.update()

    def errorDialog(message):
        """Error dialog box"""

        if has_tk():
            from tkMessageBox import showerror

            showerror(title, message)
            tk_flush()
        else:
            print(message)

    def messageDialog(message):
        """Error dialog box"""
        if has_tk():
            from tkMessageBox import showinfo

            showinfo(title, message)
            tk_flush()
        else:
            print(message)

    def askRetryCancel(message):
        if has_tk():
            from tkMessageBox import askretrycancel

            r = askretrycancel(title, message)
            tk_flush()
            return r

    def askYesNo(message):
        if has_tk():
            from tkMessageBox import askyesno

            r = askyesno(title, message)
            tk_flush()
            return r

    def askPassword(realm, username):
        if has_tk():
            from tkSimpleDialog import askstring

            r = askstring(
                title,
                "Please enter the password for '%s' in '%s'" % (username, realm),
                show="*",
            )
            tk_flush()
            return r


def fatalError(message, exit=1):
    """Show error message and exit"""
    global log_file
    msg = (
        _(
            """FATAL ERROR: %s
            ZopeEdit will close."""
        )
        % message
    )
    errorDialog(msg)
    # Write out debug info to a temp file
    if log_file is None:
        log_file = mktemp(suffix="-zopeedit-traceback.txt")
    debug_f = open(log_file, "a+b")
    try:
        # Copy the log_file before it goes away on a fatalError.
        traceback.print_exc(file=debug_f)

    finally:
        debug_f.close()
    if exit:
        sys.exit(0)


def messageScrolledText(text):
    if has_tk():
        from ScrolledText import ScrolledText

        myText = ScrolledText(tk_root, width=80, wrap="word")
        myText.pack()
        myText.insert("end", "".join(text))
        tk_root.wm_deiconify()
        tk_flush()
        tk_root.protocol("WM_DELETE_WINDOW", sys.exit)
        tk_root.mainloop()

    else:
        print("".join(text))


default_configuration = (
    """
#######################################################################
#                                                                     #
#       Zope External Editor helper application configuration         #
#                                                                     #
#             maintained by atReal contact@atreal.fr                  #
#######################################################################
#                                                                     #
# Remove '#' to make an option active                                 #
#                                                                     #
#######################################################################

[general]
# General configuration options
version = %s
"""
    % __version__
)

default_configuration += """
# Create a new version when the file is closed ?
#version_control = 0

# Temporary file cleanup. Set to false for debugging or
# to waste disk space. Note: setting this to false is a
# security risk to the zope server
#cleanup_files = 1
#keep_log = 1

# Use WebDAV locking to prevent concurrent editing by
# different users. Disable for single user use or for
# better performance
# set use_locks = 0 if you use a proxy that does not allow wabdav LOCKs
#use_locks = 1

# If you wish to inform the user about locks issues
# set manage_locks = 1
# This will allow the user to borrow a lock or edit a locked file
# without informing the administrator
#manage_locks = 1

# To suppress warnings about borrowing locks on objects
# locked by you before you began editing you can
# set this flag. This is useful for applications that
# use server-side locking, like CMFStaging
#always_borrow_locks = 0

# Duration of file Lock : 1 day = 86400 seconds
# If this option is removed, fall back on 'infinite' zope default
# Default 'infinite' value is about 12 minutes
#lock_timeout = 86400

# Proxy address
#proxy = http://www.myproxy.com:8080

# Proxy user and password ( optional )
#proxy_user = 'username'
#proxy_pass = 'password'

# Automatic proxy configuration from system
# does nothing if proxy is configured
# Default value is "disabled" : 0
#autoproxy = 1

# Max isAlive counter
# This is used in order to wait the editor to effectively lock the file
# This is the number of 'probing' cycles
# default value is 5 cycles of save_interval
#max_isalive_counter = 5

# Automatic save interval, in seconds. Set to zero for
# no auto save (save to Zope only on exit).
#save_interval = 5

# log level : default is 'info'.
# It can be set to debug, info, warning, error or critical.
#log_level = debug

# If your server is not using utf-8
#server_charset = utf-8

# If your client charset is not iso-8859-1
# client_charset = iso-8859-1

# Lock File Scheme
# These are schemes that are used in order to detect "lock" files
# %s is the edited file's name (add a ';' between each scheme):
#lock_file_schemes = .~lock.%s#;~%s.lock;.%s.swp

"""

if linux:
    default_configuration += """
# Uncomment and specify an editor value to override the editor
# specified in the environment. You can add several editors separated by ';'

# Default editor
#editor = gedit;kwrite;gvim;emacs;nano;vi

# Environment auto-launcher
# based on the association between mime type and applications
#autolaunchers = gnome-open;kde-open;xdg-open

# Specific settings by content-type or meta-type. Specific
# settings override general options above. Content-type settings
# override meta-type settings for the same option.

[meta-type:DTML Document]
extension=.dtml

[meta-type:DTML Method]
extension=.dtml

[meta-type:Script (Python)]
extension=.py

[meta-type:Page Template]
extension=.pt

[meta-type:Z SQL Method]
extension=.sql

[content-type:text/plain]
extension=.txt

[content-type:text/html]
extension=.html

[content-type:text/xml]
extension=.xml

[content-type:text/css]
extension=.css

[content-type:text/javascript]
extension=.js

[general-type:image/*]
editor=gimp -n

[content-type:application/x-xcf]
editor=gimp -n

[content-type:application/vnd.oasis.opendocument.text]
extension=.odt
editor=

[content-type:application/vnd.sun.xml.writer]
extension=.sxw
editor=

[content-type:application/vnd.sun.xml.calc]
extension=.sxc
editor=

[content-type:application/vnd.oasis.opendocument.spreadsheet]
extension=.ods
editor=

[content-type:application/vnd.oasis.opendocument.presentation]
extension=.odp
editor=

[content-type:application/msword]
extension=.doc
editor=

[content-type:application/vnd.ms-excel]
extension=.xls
editor=

[content-type:application/vnd.ms-powerpoint]
extension=.ppt
editor=

[content-type:application/x-freemind]
extension=.mm
editor=freemind

[content-type:text/xml]
extension=.planner
editor=planner
"""


def main():
    """ call zopeedit as a lib
    """
    args = sys.argv
    input_file = ""

    if "--version" in args or "-v" in args:
        credits = (
            "Zope External Editor %s\n" "By atReal\n" "http://www.atreal.net"
        ) % __version__
        messageDialog(credits)
        sys.exit(0)
    if "--help" in args or "-h" in args:
        # Open the VERSION file for reading.
        try:
            f = open(os.path.join(system_path, "docs", "README.txt"), "r")
        except IOError:
            # zopeedit is not properly installed : try uninstalled path
            f = open(os.path.join(system_path, "..", "..", "README.txt"), "r")
        README = f.readlines()
        f.close()
        messageScrolledText(README)
        sys.exit(0)

    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
        try:
            ExternalEditor(input_file).launch()
        except (KeyboardInterrupt, SystemExit):
            pass
        except:
            fatalError(sys.exc_info()[1])
    else:
        ExternalEditor().editConfig()


if __name__ == "__main__":
    """ command line call
    """
    main()
