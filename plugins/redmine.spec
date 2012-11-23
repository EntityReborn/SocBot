[general]
redmineurl = string(default='')
passiveformat = string(default={url})
activeformat = string(default=[ {project}/{tracker}/{status} ] "{subject}" by {author} on {date} ( {url} ))
activetriggerers = list(default=list())
passiveregex = string(default=(?:(?:bugs?|issues?|tickets?)\s*)?#(\d+))
cookie = string(default='')