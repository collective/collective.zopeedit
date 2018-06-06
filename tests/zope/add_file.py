from OFS.Image import manage_addFile
import transaction

def main(app):
    manage_addFile(app, 'test_external') 
    transaction.commit()


# If this script lives in your source tree, then we need to use this trick so that
# five.grok, which scans all modules, does not try to execute the script while
# modules are being loaded on the start-up
if "app" in locals():
    main(app)

