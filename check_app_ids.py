import src.run_api as run_api
import class_demo.user_api as api_mod

print('run_api.app id', id(run_api.app))
print('api_mod.app id', id(api_mod.app))
print('same?', run_api.app is api_mod.app)
