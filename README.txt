Zope External Editor
====================

Introduction
------------

  The Zope External Editor is a new way to integrate Zope more seamlessly with
  client-side tools. It has the following features:
    
  - Edit objects locally, directly from the ZMI or from your web application.
  
  - Works with any graphical editor application that can open a file from the 
    command line, including: emacs, gvim, xemacs, nedit, gimp, openoffice.org,
    MS Office, Photoshop, etc.

  - Automatically saves changes back to Zope without ending the editing session.

  - Associate any client-side editor application with any Zope object by
    meta-type or content-type. Both text and binary object content can be
    edited.

  - Locks objects while they are being edited. Automatically unlocks them when
    the editing session ends.

  - Can add file extensions automatically to improve syntax highlighting or 
    file type detection.
  
  - Works with basic auth, cookie auth and Zope versions. Credentials are
    automatically passed down to the helper application. No need to
    reauthenticate.
    
  - https support (Openssl required)
  
  - proxy support (might fail with some proxies ; contact us if you get
    an issue)
  
Using It
--------

    Use of the application is about as easy as using the ZMI once your browser
    is configured (see the installation instructions). To edit an object
    externally, just click on the pencil icon next to the object in the ZMI,
    or on the specific direct edit action in your application.
    The object will be downloaded and opened using the editor application you
    have chosen (you will be prompted the first time to choose an editor). 

    You edit the object just like any other file. When you save the changes in
    your editor, they are automatically uploaded back to Zope in the
    background. While the object is open in your editor, it is locked in Zope
    to prevent concurrent editing. When you end your editing session (ie you
    close your editor) the object is unlocked.

How it Works
------------
  
    Ok, so this all sounds a bit too good to be true, no? So how the heck does
    it work anyway? First I'll give you a block diagram::
    
      +------------+     +------------+     +---------+        +------+
      | Editor App | <-- | Helper App | <-- | Browser | <-/ /- | Zope |
      +------------+     +------------+     +---------+        +------+
                  ^       ^     ^                                ^
                   \     /       \                              /
                    v   v         -----------------------/ /----
                   -------
                  / Local \
                  \  File /
                   -------
                   
    Now the key to getting this to work is solving the problem that the editor
    cannot know about Zope, and must only deal with local files. Also, there is
    no standard way to communication with editors, so the only communication
    channel can be the local file which contains the object's content or code.
    
    It is trivial to get the browser to fire up your editor when you download
    a particular type of data with your browser. But that does you little good,
    since the browser no longer involves itself once the data is downloaded. It
    just creates a temp file and fires off the registered application, passing
    it the file path. Once the editor is running, it is only aware of the local
    file, and has no concept of where it originated from.
    
    To solve this problem, we have developed a helper application whose job is
    essentially two-fold:
    
    - Determine the correct editor to launch for a given Zope object
    
    - Get the data back into Zope when the changes are saved

    So, let's take a step by step look at how it works:

    1. You click on the external editor link (the pencil icon) in the Zope 
       management interface (This might be a special action).
       
    2. The product code on the server creates a response that encapsulates the
       necessary meta-data (URL, meta-type, content-type, cookies, etc) and the
       content of the Zope object, which can be text or binary data. The
       response has the contrived content-type "application/x-zope-edit" and
       the file extension ".zem".

    3. The browser receives the request, and finds our helper application
       registered for "application/x-zope-edit" or the extension ".zem".
       It saves the response data locally to disk and spawns the helper app
       to process it.

    4. The helper app, reads its config file and the response data file. The
       meta-data from the file is parsed and the content is copied to a new
       temporary file. The appropriate editor program is determined based on
       the data file and the configuration.
       
    5. The editor is launched as a sub-process of the helper app, passing it the
       file containing the content data.
       
    6. If so configured, the helper app sends a WebDAV lock request back to Zope
       to lock the object.
       
    7. Every so often (if so configured), the helper app stats the content file
       to see if it has been changed. If so, it sends an HTTP PUT request
       back to Zope containing the new data.
       
    8. When the editor is closed, the content file is checked one more time and
       uploaded if it has changed. Then a WebDAV unlock request is sent to Zope.
       
    9. The helper application exits.
    
Configuration
-------------
  
    The helper application supports several configuration options, each of
    which can be triggered in any combination of object meta-type, content-type
    or domain. This allows you to create appropriate behavior for different
    types of Zope objects and content or even different servers. The
    configuration file is stored in the file  "~/.zope-external-edit" (Unix) or
    "~\ZopeEdit.ini" (Windows). If no configuration file is found when the
    helper application starts, a default config file is created in your home
    directory.

    The configuration file follows the standard Python ConfigParser format,
    which is pretty much like the old .ini file format from windows. The file
    consists of sections and options in the following format::

      [section 1]
      option1 = value
      option2 = value

      [section 2]
      ...
    
    Options
    
      The available options for all sections of the config file are:

      editor -- Command line or plugin name used to invoke the editor
      application. On Windows, if no editor setting is found for an object you
      edit, the helper app will search the file type registry for an
      appropriate editor based on the content-type or file extension of the
      object (which can be specified using the extension option below). By
      default, the file path of the local file being edited is appended to
      this command line. To insert the file path in the middle of your
      command, use "$1" for Unix and "%1" for Windows respectively.

      save_interval -- (float) The interval in seconds that the helper 
      application checks the edited file for changes.

      use_locks -- (1 or 0) Whether to use WebDAV locking. The user editing must
      have the proper WebDAV related permissions for this to work.
      
      always_borrow_locks -- (1 or 0) When use_locks is enabled this features
      suppresses warnings when trying to edit an object you have already locked.
      When enabled, external editor will always "borrow" the existing lock token
      instead of doing the locking itself. This is useful when using CMFStaging
      for instance. If omitted, this option defaults to 0.

      cleanup_files -- (1 or 0) Whether to delete the temp files created.
      WARNING the temp file coming from the browser contains authentication
      information and therefore setting this to 0 is a security risk,
      especially on shared machines. If set to 1, that file is deleted at the
      earliest opportunity, before the editor is even spawned. Set to 0 for
      debugging only.

      extension -- (text) The file extension to add to the content file. Allows
      better handling of images and can improve syntax highlighting.

      temp_dir -- (path) Path to store local copies of object data being
      edited. Defaults to operating system temp directory. *Note: this setting
      has no apparent effect on Windows* 8^(
      
      long_file_name -- (1 or 0) Whether to include the whole path to the 
      object including the hostname in the file name (the default) or just the
      id of the object being edited. Turn this option off for shorter file
      names in your editors, and for editors that don't like long names.

      file_name_separator -- (string) Character or characters used to separate
      path elements in long files names used by external editor. Defaults to
      a comma (,). This must be a legal character for use in file names on
      your platorm (i.e., don't use a path separator character!). This option
      is ignored if 'long_file_name' is set to 0.

    Sections
    
      The sections of the configuration file specify the types of objects and
      content that the options beneath them apply to.
      
      There is only one mandatory section '[general]', which should define all
      of the above options that do not have a default value. If no other
      section defines an option for a given object, the general settings are
      used.

      Additional sections can apply to a particular domain, content-type or
      meta-type. Since objects can have all these properties, the options are
      applied in this order of precedence.

      - '[content-type:text/html]' -- Options by whole content-type come first
      
      - '[content-type:text/\*]' -- Options by major content-type come second.
      
      - '[meta-type:File]' -- Options by Zope meta-type are third.

      - '[domain:www.mydomain.com]' -- Options by domain follow. Several
        sections can be added for each domain level if desired.
      
      - '[general]' -- General options are last.
      
      This scheme allows you to specify an extension by content-type, the
      editor by meta-type, the locking settings by domain and the remaining 
      options under general for a given object.
      
  Editor Plugins

    For tighter client-side integration, external editor has a plugin system
    that allows it to interact directly with supported applications.

    On Windows this generally means using COM to invoke the application, open
    the content file and wait for the user to save and close the file. Because
    each application has different remote scripting capabilities and APIs,
    editor specific plugins must be written tailored to each supported
    application and platform.

    This system allows external editor to efficiently connect to running
    applications without relaunching them and therefore fully support MDI 
    environments. The following applications currently have plugin support::

      Application       Platform    Plugin Module Name(s)
      ===================================================
      HomeSite          Windows     homesite5, homesite
      Dreamweaver       Windows     dreamweaver	

    External editor will attempt to load a plugin for any application before
    using the general editor control method. It does this by matching the
    name of the application executable file (sans extension) in the editor
    command line with the available plugins. 

    Because plugins do not require the path of the editor application to work,
    you can simply specify the plugin module name for your editor in the
    configuration file if desired. For example, to specify Photoshop for all
    image files, use add the following section to your config file
    (ZopeEdit.ini on Windows)::

      [content-type:image/*]
      editor=photoshop

    This is only a shortcut and specifying the full application path will
    still use the plugin where possible.

    Plugin Notes

      Photoshop -- Photoshop's COM API is quite limited, and external editor
      cannot detect that you have closed a file until you exit the entire
      application (it can still detect saves). Therefore you may want to turn 
      off DAV locking (use_locks=0) or borrow locks (always_borrow_locks=1)
      when using it.

      Dreamweaver -- External editor cannot detect when you have finished 
      editing a single file. Objects edited with Dreamweaver will remain
      locked on the server until you exit the application. As with Photoshop
      above, you may want to turn off locking for Dreamweaver.

      If your favorite editor needs a plugin because the general support is
      not good enough, please let me know. Keep in mind that I must be able to
      run a copy of the application in order to develop a plugin for it. So, 
      unless the application is free, or a full demo is available for download
      I won't be able to help much. Plugins are not difficult to write, and I
      encourage you to write one for your favorite editor, start by reading
      one of the existing ones. I am happy to include third-party plugins with
      the distribution.
    
  Permissions
  
    External editing is governed by the permission "Use external editor".
    Users with this permission can launch external editor from editable
    objects. In order to save changes, users will need additional permissions
    appropriate for the objects they are editing.
    
    If users wish to use the built-in locking support, they must have the
    "WebDAV access", "WebDAV Lock items" and "WebDAV Unlock items" permissions
    for the objects they are editing.
    
    If these permissions are not set in Zope, then the helper application will
    receive unauthorized errors from Zope which it will present to the user.
      
  Integrating with External Editor
  
    The external editor product in zope installs a globally available object
    that can format objects accessible through FTP/DAV for use by the helper
    application. You can take advantage of this functionality easily in your
    own content management applications.
    
    Say you have an FTP editable object, "document", in a Zope folder named
    "my_stuff". The URL to view the object would be::
    
      http://zopeserver/my_stuff/document
      
    The URL to kick off the external editor on this document would be::
    
      http://zopeserver/my_stuff/externalEdit_/document
      
    Now, this may look a bit odd to you if you are used to tacking views on to
    the end of the URL. Because '\externalEdit_' is required to work on Python
    Scripts and Page Templates, which swallow the remaining path segments on
    the URL following themselves, you must put the call to '\externalEdit_'
    *directly before* the object to be edited. You could do this in ZPT using
    some TAL in a Page Template like::

      <a href='edit' 
         attributes='href
         string:${here/aq_parent/absolute_url}/externalEdit_/${here/getId}'>
         Edit Locally
      </a>
      
    As an alternative, you can also pass the path the object you want to edit
    directly to the \externalEdit_ object when you call its index_html method.
    It can be called either directly by URL or from a python script.
    \externalEdit_ will return the proper response data for the object to edit.
    Here are some examples::

      http://zopeserver/externalEdit_?path=/my_stuff/document
      
      return context.externalEdit_.index_html(
          context.REQUEST, context.RESPONSE, path='/my_stuff/document')

    When integrating External Editor with a CMS that already uses DAV
    locks, it will, by default allow users to borrow locks made on the server
    after displaying a confirmation dialog box. Although you can make this
    automatic by specifying 'always_borrow_locks = 1' in the External Editor
    config file, it may be desireable to make this the default behavior when
    using that server. To facilitate this, you can specify that locks 
    should be automatically borrowed in the URL (New in 0.7)::

      http://zopeserver/my_stuff/externalEdit_/document?borrow_lock=1
      
    External Editor also defines a global method that you can call to insert
    pencil icon links for appropriate objects. The method automatically checks
    if the object supports external editing and whether the user has the "Use
    external editor" permission for that object. If both are true, it returns
    the HTML code to insert the external editor icon link. Otherwise it returns
    an empty string.

    The method is '\externalEditLink_(object)'. The object argument is the
    object to create the link for if appropriate. Here is some example page
    template code that inserts links to objects in the current folder and the
    external editor icon where appropriate::

      <div tal:repeat="object here/objectValues">
        <a href="#" 
           tal:attributes="href object/absolute_url"
           tal:content="object/title_or_id">Object Title</a>
        <span tal:replace="structure python:here.externalEditLink_(object)" />
      </div>       

Conclusion
----------
  
    I hope you enjoy using this software. If you have any comments, suggestions
    or would like to report a bug, send an email to this version maintainer:
    
      Thierry Benita
      
      contact@atreal.net

      http://www.atreal.net


Special thanks for their help and contributions
-----------------------------------------------

      * Wayne Glover - excellent texting and reports makes ZopeEdit go ahead !

      * Alexandre Gouraud - contributor of the Digest authentification method

Authors
---------

(c) 2010, Thierry Benita, Jean-Nicolas Bes, atReal, Casey Duncan, contributors atReal and Zope Corporation. All rights reserved.
