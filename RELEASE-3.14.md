# Umbrale Companion 3.14

Malformed thousands grouping such as1,2or1,,000 is kept uncertain rather than silently converted to another number. Valid plain, comma-grouped and space-split amounts remain supported.

Rows containing multiple reward amount introducers are kept uncertain, including when a second amount is unreadable. This prevents assigning EXP digits to a party bonus or mesos message when OCR merges lines.

Includes prior context, party EXP, money confidence and compact UI fixes. Tested with supplied images, synthetic scenarios and isolated native UI; not live gameplay. Unread notices can still leave totals incomplete.

Close the companion before installing program files. Preserve state.json and caches.
