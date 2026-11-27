# coding:utf-8

# ---------------------------------------------------------------------------------
# PM-Linux面板
# ---------------------------------------------------------------------------------
# Licensed under the Apache License 2.0. See LICENSE and NOTICE.
# ---------------------------------------------------------------------------------


from .dashboard import blueprint as DashboardModule
from .site import blueprint as SiteModule
from .task import blueprint as TaskModule
from .setting import blueprint as SettingModule
from .logs import blueprint as LogsModule
from .files import blueprint as FilesModule
from .soft import blueprint as SoftModule
from .plugins import blueprint as PluginsModule
from .crontab import blueprint as CrontabModule
from .firewall import blueprint as FirewallModule
from .monitor import blueprint as MonitorModule
from .system import blueprint as SystemModule
from .database import blueprint as DatabaseModule

def get_submodules():
    return [
        DashboardModule,
        SiteModule,
        TaskModule,
        LogsModule,
        FilesModule,
        SoftModule,
        PluginsModule,
        CrontabModule,
        FirewallModule,
        MonitorModule,
        SystemModule,
        DatabaseModule,
        SettingModule,
    ]
