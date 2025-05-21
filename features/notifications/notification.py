Updating imports to use PostgreSQL-based events instead of Redis.
```

```python
from datetime import datetime
from common.events import publish_event, EventChannels
from common.db import db
from common.db_models import NotificationModel