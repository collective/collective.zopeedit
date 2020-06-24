""" External Editor Plugins """


def importAll():
    # Assert plugin dependancies for py2exe
    # All plugins must be imported here to be distributed
    # in the Windows binary package!
    import homesite, homesite5
