# Purpose

Generate information about issues within an github epic

# Requirements

1. python2
2. An ssh alias to Gerrit `openbmc.gerrit`
3. config.py file with 
 #!/usr/bin/python
 zen_auth = {
    'X-Authentication-Token': 'TOKEN',
 }

 GITHUB_USER = 'github id'
 GITHUB_PASSWORD = '<password>'


To obtain a zenhub TOKEN
https://dashboard.zenhub.io/#/settings


# Usages

Generate a list of issues within a github epic:

```
sprint-report.py -e <epic number> report
sprint-report.py -e <epic number> -csv report
```



