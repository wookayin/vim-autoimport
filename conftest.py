# During unit test, the vim module might not be present.
# Therefore we should mock vim module before importing any packages.
import sys
sys.modules['vim'] = type(sys)('vim')
