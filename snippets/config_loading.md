# 配置加载代码片段

```python
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取配置
api_key = os.getenv('API_KEY')
storage_path = os.getenv('STORAGE_PATH', './storage')
```
