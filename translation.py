"""Layer 4: deterministic alert wording and severity."""
FEATURE_MEANINGS = {
    'Login time': 'time of sign-in',
    'Off-hours flag': 'access outside the role schedule',
    'Records accessed': 'number of records accessed that day',
    'Session duration': 'length of the access session',
    'Access rate': 'records accessed per minute',
    'Role mismatch': 'access outside the role’s allowed departments',
    'Unassigned department': 'access outside the user’s assigned department',
}
GROUPS = {
    'Time': ('Login time', 'Off-hours flag'),
    'Volume': ('Records accessed', 'Session duration', 'Access rate'),
    'Role or department': ('Role mismatch', 'Unassigned department'),
}
TEMPLATES = {
    'Combined anomaly': '{context} Multiple signals supported the flag. {details}',
    'Burst behavior': '{context} The {duration}-minute session averaged {rate:.1f} records per minute.',
    'Excessive access': '{context} The daily access pattern stood out for this role. {details}',
    'Off-hours access': '{context} The sign-in pattern stood out for this role. {details}',
    'Role mismatch': '{context} {department} is outside this role’s allowed departments.',
    'Unassigned access': '{context} The role can access {department}, but this user is assigned to {assigned}.',
    'Fallback': '{context} The strongest signals supporting the flag were {drivers}.',
}

def translate(row, features):
    # Negative Tree SHAP values shorten path length. The pipeline flips their sign
    # for display so positive means the feature supports the anomaly flag.
    values = dict(zip(features, row['shap'], strict=True))
    levels = {name: ('High' if score > .7 else 'Medium' if score >= .3 else 'Low')
              for name, score in values.items()}
    active = {group for group, names in GROUPS.items()
              if any(levels[name] != 'Low' for name in names)}
    duration = row['session_duration_mins']
    count = row['records_accessed']
    rate = count / duration
    baseline = row['baseline']
    volume = 'Volume' in active
    short = duration <= 4
    burst = volume and short and rate >= 3
    if len(active) >= 2:
        template = 'Combined anomaly'
    elif burst:
        template = 'Burst behavior'
    elif volume and not short:
        template = 'Excessive access'
    elif active == {'Time'}:
        template = 'Off-hours access'
    elif active == {'Role or department'} and row['role_mismatch']:
        template = 'Role mismatch'
    elif active == {'Role or department'} and row['department_accessed'] != row['assigned_department']:
        template = 'Unassigned access'
    else:
        template = 'Fallback'

    if burst or {'Time', 'Volume'} <= active or len(active) == 3:
        severity = 'High'
    elif len(active) == 2 or (len(active) == 1 and 'High' in levels.values()):
        severity = 'Medium'
    elif len(active) == 1:
        severity = 'Low'
    else:
        severity = 'Low'

    reasons = []
    if 'Time' in active:
        if row['off_hours_access']:
            reasons.append(f"Access was outside the role’s {row['hours']} schedule.")
        else:
            reasons.append(f"Sign-in time ({row['login_time']}) influenced the score, within the role’s {row['hours']} schedule.")
    if levels['Records accessed'] != 'Low' and count > baseline:
        reasons.append(f'The daily total was {count / baseline:.1f}× the role’s average of {baseline:g} records per day.')
    if levels['Session duration'] != 'Low':
        reasons.append(f'The session lasted {duration} minutes.')
    if levels['Access rate'] != 'Low':
        reasons.append(f'The session averaged {rate:.1f} records per minute.')
    if 'Role or department' in active:
        if row['role_mismatch']:
            reasons.append(f"{row['department_accessed']} is outside the role’s allowed departments.")
        elif row['department_accessed'] != row['assigned_department']:
            reasons.append(f"The user is assigned to {row['assigned_department']}.")
    ordered = sorted(values, key=values.get, reverse=True)
    drivers = ', '.join(FEATURE_MEANINGS[name] for name in ordered[:2])
    context = (f"{row['role']} ({row['user_id']}) accessed {count} records in "
               f"{row['department_accessed']} at {row['login_time']} on {row['date']}.")
    details = ' '.join(reasons) or f'The strongest signals supporting the flag were {drivers}.'
    action = ('Prioritize this event for review.' if severity == 'High'
              else 'Review the event against the user’s expected duties.')
    body = TEMPLATES[template].format(context=context, details=details, duration=duration,
                                     rate=rate, department=row['department_accessed'],
                                     assigned=row['assigned_department'], drivers=drivers)
    return dict(template=template, severity=severity, levels=levels, groups=sorted(active),
                message=f'{body} {action}', context=context, action=action,
                reasons=reasons or [f'Model signals: {drivers}.'])
