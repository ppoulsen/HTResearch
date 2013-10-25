import unittest

loader = unittest.TestLoader()
#grab any .py file with the word test in it ...
tests = loader.discover('.', pattern='*[test|tests].py')
testRunner = unittest.TextTestRunner(verbosity=2)
testRunner.run(tests)