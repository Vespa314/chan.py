## Purpose

提供预警提醒能力：对价格触发、买卖点出现、监控卖点等事件设置提醒，触发时通知用户。

## ADDED Requirements

### Requirement: 预警规则设置
系统 SHALL 允许用户设置预警规则，包括价格触发、买卖点出现与监控卖点等事件类型。

#### Scenario: 设置预警规则
- **WHEN** 用户设置一条预警规则
- **THEN** 规则被持久化并开始生效

### Requirement: 预警触发与通知
系统 SHALL 在预警条件满足时触发提醒并通知用户。

#### Scenario: 触发提醒
- **WHEN** 预警条件满足
- **THEN** 系统触发提醒并通知用户
