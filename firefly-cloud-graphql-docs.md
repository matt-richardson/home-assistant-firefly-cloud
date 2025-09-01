
=== GraphQL Schema Introspection ===
=== Schema Overview ===
Query Type: Query
Mutation Type: Mutation
Subscription Type: undefined

=== Available Root Queries ===
• app_styles: [AppStyle]
• configuration: FireflyConfiguration!
• events: [Event]
  Args: for_guid: String, start: String, end: String
• groups: [Group]
  Args: guids: [String]
• lesson_plans: [LessonPlan]
  Args: for_guids: [String]
• tasks: [Task]
  Args: ids: [Int], set_by: String, set_to: String, for_recipient: String, updated_since: String
• user_notes: [UserNote]
  Args: created_by: String
• users: [User]
  Args: guid: String

=== Available Mutations ===
• bookmarks: [Bookmark]
  Args: guids: [String], new_delete: Boolean
• groups: [Group]
  Args: new: Boolean, new_name: String, new_members: [String]
• lesson_plans: [LessonPlan]
  Args: event_guid: String, new_note: String
• messages: [Message]
  Args: user_guid: String, ids: [Int], new_read: Boolean, new_archive: Boolean
• targets: [Target]
  Args: new_target: String, new_teacher_guid: String, new_student_guid: String, new_group_guid: String
• tasks: [Task]
  Args: ids: [Int], new: Boolean, new_delete: Boolean, new_title: String, new_setter: String, new_description: String, new_archived: Boolean, new_draft: Boolean, new_set: String, new_due: String, new_markbook_displaymode: String, new_show_in_markbook: Boolean, new_highlight_in_markbook: Boolean, new_parentportal_visible: Boolean, new_hide_addressees: Boolean, new_addressees: [String], new_attachments: [Attachment], new_task_type: String, new_pseudo_from: String, new_pseudo_to: String, new_hide_from_recipients: Boolean, new_file_submission_required: Boolean, new_assessment_type: Int, new_total_mark_out_of: Int, new_rubric_id: Int
• user_note: [UserNote]
  Args: new: Boolean, new_note: String, new_author: String, new_user: String, new_created: String, new_delete: Boolean, ids: [Int]

=== Object Types ===

AddFileEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    file: ResourceInfo
      The file attached to this event

AppStyle:
  Fields:
    name: String!
      The name of the style.
    value: String
      The value for the style.
    type: String!
      The type of style.
    file: String
      The base64 representation of the file.

Attachment:
  Fields:
    filename: String!
      The filename for the file.
    binary_base64: String!
      The base64 encoded binary information for the file.

BookmarkDeletedType:
  Implements: Bookmark
  Fields:
    guid: String!
      The bookmark guid.
    deleted: Boolean!
      Is the bookmark deleted?

CommentEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    message: Unknown
      The message associated with this response event

ConfirmStudentIsExcusedEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    message: Unknown
      The message associated with this response event

ConfirmStudentIsUnexcusedEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    message: Unknown
      The message associated with this response event

ConfirmTaskIsCompleteEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    message: Unknown
      The message associated with this response event

Event:
  Fields:
    guid: String!
      The guid for the event.
    description: String!
      The description for the event.
    start: String!
      The start instant for the event.
    end: String!
      The end instant for the event.
    local_start: String!
      The start instant for the event in the server's local timezone.
    local_end: String!
      The end instant for the event in the server's local timezone.
    location: String!
      The location for the event.
    subject: String!
      The subject for the event.
    attendees: [EventAttendee]!
      The users attending the event.
    lesson_plan: LessonPlan
      The lesson plan for the event.

EventAttendee:
  Fields:
    principal: Principal
      The user/group information for the event attendee.
    role: String!
      The role for the attendee at the event.

FireflyConfiguration:
  Fields:
    week_start_day: String!
      The day on which a week will start for this school
    weekend_days: [String]!
      A list of days that are considered weekend days for this school
    academic_year_start: String!
      The date on which the current academic year started
    academic_year_end: String!
      The date on which the current academic year will finish
    native_app_capabilities: [String]
      A list of capabilities the native apps can provide.
    notice_group_guid: String!
      The send notice group guid.
    netMedia_url: String
      The url for NetMedia
    schoolpost_url: String
      The url for SchoolPost

Group:
  Fields:
    guid: String!
      The guid of the group.
    name: String!
      The name of the group.
    sort_key: String!
      The sort key for the group.
    profile_url: String!
      The URL to this group's profile page
    members: [GroupMember]
      The members of the group.
    personal_colour: String
      The colour assigned to the logged in user for the group.
    contains_non_students: Boolean!
      Whether the group contains non-students

GroupMember:
  Fields:
    principal: User
      The user/group information for the group member.
    targets: [Target]
      The target(s) for this group member.
      Args: for_guid: String

LessonPlan:
  Fields:
    event_guid: String!
      The guid for the lesson plans events.
    note: String!
      The lesson plan contents.
    updated: String
      The instant the lesson plan was last updated.
    author: User
      The author of the lesson plan.

MarkAndGradeEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    message: Unknown
      The message associated with this response event
    mark: Unknown
      The mark associated with this response event
    outOf: Unknown
      The maximum possible mark associated with this response event
    grade: Unknown
      The grade associated with this response event

MarkAsDoneEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.

MarkAsUndoneEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.

Message:
  Fields:
    id: Int!
      The id of the message.
    from: Principal
      The person who sent the message.
    single_to: Principal
      The entity the message was sent to, if sent to one principal.
    all_recipients: String!
      A string containing all recipients the message was sent to.
    body: String!
      The body of the message.
    sent: Date!
      The time the message was sent.
    archived: Boolean!
      Has the message been archived?
    read: Boolean!
      Has the message been read?

Mutation:
  Fields:
    bookmarks: [Bookmark]
      Args: guids: [String], new_delete: Boolean
    groups: [Group]
      Args: new: Boolean, new_name: String, new_members: [String]
    lesson_plans: [LessonPlan]
      Args: event_guid: String, new_note: String
    messages: [Message]
      Args: user_guid: String, ids: [Int], new_read: Boolean, new_archive: Boolean
    targets: [Target]
      Args: new_target: String, new_teacher_guid: String, new_student_guid: String, new_group_guid: String
    tasks: [Task]
      Args: ids: [Int], new: Boolean, new_delete: Boolean, new_title: String, new_setter: String, new_description: String, new_archived: Boolean, new_draft: Boolean, new_set: String, new_due: String, new_markbook_displaymode: String, new_show_in_markbook: Boolean, new_highlight_in_markbook: Boolean, new_parentportal_visible: Boolean, new_hide_addressees: Boolean, new_addressees: [String], new_attachments: [Attachment], new_task_type: String, new_pseudo_from: String, new_pseudo_to: String, new_hide_from_recipients: Boolean, new_file_submission_required: Boolean, new_assessment_type: Int, new_total_mark_out_of: Int, new_rubric_id: Int
    user_note: [UserNote]
      Args: new: Boolean, new_note: String, new_author: String, new_user: String, new_created: String, new_delete: Boolean, ids: [Int]

PageInfo:
  Fields:
    id: Int!
      The id for the page.
    title: String!
      The title for the page.

Principal:
  Fields:
    guid: String!
      The guid of the principal.
    name: String!
      The name of the principal.
    profile_url: String!
      The URL to this principal's profile page
    sort_key: String!
      The sort key for the principal.
    group: Group
      The group object if the principal is a group.

ProfilePermissions:
  Fields:
    can_read_tasks: Boolean!
      Whether the task read profile permission exists
    can_read_marks_and_feedback: Boolean!
      Whether the marks and feedback read profile permission exists

Query:
  Fields:
    app_styles: [AppStyle]
    configuration: FireflyConfiguration!
    events: [Event]
      Args: for_guid: String, start: String, end: String
    groups: [Group]
      Args: guids: [String]
    lesson_plans: [LessonPlan]
      Args: for_guids: [String]
    tasks: [Task]
      Args: ids: [Int], set_by: String, set_to: String, for_recipient: String, updated_since: String
    user_notes: [UserNote]
      Args: created_by: String
    users: [User]
      Args: guid: String

ReminderEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.

RequestResubmissionEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    message: Unknown
      The message associated with this response event

ResourceInfo:
  Fields:
    id: Int!
      The resource id for the file.
    filename: String!
      The filename for the file.
    filetype: String!
      The mimetype the file.
    filesize: Int!
      The size of the file.
    etag: String!
      The HTTP Etag for the file.

RevertTaskToToDoEventType:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    message: Unknown
      The message associated with this response event

StampResponseAsSeenEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.
    message: Unknown
      The message associated with this response event

Target:
  Fields:
    group: Group!
      The group that this target is associated with.
    student: User!
      The student that this target representing.
    teacher: User!
      The teacher who set this target.
    target: String!
      The target.

TaskArchiveEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.

TaskDeletedViewType:
  Implements: Task
  Fields:
    id: Int!
      The id of the task.
    deleted: Boolean!
      The task is deleted.

TaskEditEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.

TaskFullViewType:
  Implements: Task
  Fields:
    id: Int!
      The id of the task.
    deleted: Boolean!
      The task is deleted.
    title: String!
      The title of the task.
    description: String!
      The html description of the task.
    description_page_url: String
      The url of the task description.
    complex_description: Boolean!
      Is the description complex.
    archived: Boolean!
      Has the task been archived.
    page_id: Int!
      The page associated with the task.
    setter: Principal
      The due date of the task.
    set: String!
      The set instant of the task.
    due: String
      The due date of the task.
    attachment_files: [ResourceInfo]
      The file attachments that have been set against the task.
    attachment_pages: [PageInfo]
      The attachments that have been set against the task.
    events_for_all_recipients: [TaskResponseEvent]
      The user/group information for the group member.
    task_type: String!
      Type of the task (e.g. markbook).
    pseudo_to_guid: String
      The guid for the principal who this task is proposed to be to.
    pseudo_from_guid: String
      The guid for the principal who this task is proposed to be from.
    description_contains_questions: Boolean!
      Does the task description contain questions.
    file_submission_required: Boolean!
      Does the task require a file submission.
    assessment_type: Int
      The assessment type for the task.
    total_mark_out_of: Int
      The total out of mark for the task
    assessment_details_id: Int
      The assessment details id for the task
    rubric_id: Int
      The id of the rubric for the task.
    recipients: [TaskRecipient]
      The users that have been assigned the task.
    draft: Boolean!
      Is this task a draft.
    show_in_markbook: Boolean!
      Is the task hidden from the markbook.
    highlight_in_markbook: Boolean!
      Is the task highlighted in the markbook.
    markbook_displaymode: String!
      Has the task been archived.
    response_release_mode: String!
      The attachments that have been set against the task.
    show_in_parent_portal: Boolean!
      Is the task available in the parent portal.
    hide_addressees: Boolean!
      Is the addressee list hidden from the task recipients.
    hide_from_recipients: Boolean!
      Is the task hidden from recipients.
    addressees: Unknown
      The principals the task has been set to.

TaskLimitedViewType:
  Implements: Task
  Fields:
    id: Int!
      The id of the task.
    deleted: Boolean!
      The task is deleted.
    title: String!
      The title of the task.
    description: String!
      The html description of the task.
    description_page_url: String
      The url of the task description.
    complex_description: Boolean!
      Is the description complex.
    archived: Boolean!
      Has the task been archived.
    page_id: Int!
      The page associated with the task.
    setter: Principal
      The due date of the task.
    set: String!
      The set instant of the task.
    due: String
      The due date of the task.
    attachment_files: [ResourceInfo]
      The file attachments that have been set against the task.
    attachment_pages: [PageInfo]
      The attachments that have been set against the task.
    events_for_all_recipients: [TaskResponseEvent]
      The user/group information for the group member.
    task_type: String!
      Type of the task (e.g. markbook).
    pseudo_to_guid: String
      The guid for the principal who this task is proposed to be to.
    pseudo_from_guid: String
      The guid for the principal who this task is proposed to be from.
    description_contains_questions: Boolean!
      Does the task description contain questions.
    file_submission_required: Boolean!
      Does the task require a file submission.
    assessment_type: Int
      The assessment type for the task.
    total_mark_out_of: Int
      The total out of mark for the task
    assessment_details_id: Int
      The assessment details id for the task
    rubric_id: Int
      The id of the rubric for the task.
    addressees: Unknown
      The principals the task has been set to.
    recipients: [TaskRecipient]
      The users that have been assigned the task.

TaskRecipient:
  Fields:
    principal: User!
      The user/group information for the group member.
    response_events: [TaskResponseEvent]
      The user/group information for the group member.
      Args: for_recipient: Boolean

TaskResponseEvent:
  Fields:
    guid: String
      The guid for the response event.
    created: String!
      The guid for the response event.
    deleted: Boolean!
      Has this task response event been deleted?
    latest: TaskResponseEventDetails!
      The latest version for this event.
    latest_read: Boolean!
      Has the latest version of this event been read?
    assessment_type: Int
      The assessment type of the response event.
    assessment_details_id: Int
      The id of the assessment details of the response event.
    assessment_max_mark: Int
      The max mark of the response event.

TaskSetEvent:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.

TaskUnarchiveEventType:
  Implements: TaskResponseEventDetails
  Fields:
    id: Int!
      The id of the response event.
    type: String!
      The type of response event.
    author: Principal
      The author of the response event.
    sent: String
      The instant the response event was created.
    edited: Boolean
      Is this response event an edit?
    released: Boolean
      Has this event been released.
    released_at: String
      The instant the response event was created.

User:
  Fields:
    guid: String
      The guid of the user.
    username: String!
      The username of the user.
    name: String!
      The name of the user.
    sort_key: String!
      The sort key for the user.
    participating_in: [Group]
      The groups a user is related to.
    classes: [Group]
      The classes a user is related to.
    active_classes: [Group]
      The active classes a user is related to.
    evaluated_role: String!
      The evaluated user role.
    is_admin: Boolean!
      True if the user is an administrator.
    bookmarks: [Bookmark]
      Bookmarks owned/visible by the user
    messages: [Message]
      Messages sent to the user
    sent_messages: [Message]
      Messages sent by the user
    children: [User]
    profile_permissions: ProfilePermissions

UserNote:
  Fields:
    id: Int!
      The id for the user note.
    note: String!
      The note contents.
    created: String!
      The instant the user note was created.
    author: Principal!
      The user that created the note.
    user: Principal!
      The user the note is about.

=== Interfaces ===
Task: No description
  Fields: id: Int!, title: String!, description: String!, description_page_url: String, complex_description: Boolean!, archived: Boolean!, page_id: Int!, setter: Principal, set: String!, due: String, attachment_files: [ResourceInfo], attachment_pages: [PageInfo], events_for_all_recipients: [TaskResponseEvent], task_type: String!, pseudo_to_guid: String, pseudo_from_guid: String
Bookmark: No description
  Fields: guid: String!, deleted: Boolean!
TaskResponseEventDetails: No description
  Fields: id: Int!, type: String!, author: Principal!, sent: String, released: Boolean, released_at: String, assessment_type: Int, assessment_details_id: Int, assessment_max_mark: Int

=== Custom Scalars ===
Date: The `Date` scalar type represents a timestamp provided in UTC. `Date` expects timestamps to be formatted in accordance with the [ISO-8601](https://en.wikipedia.org/wiki/ISO_8601) standard.
Decimal: No description

=== Directives ===

=== Summary ===
Total Types: 50
OBJECT: 40
INTERFACE: 3
SCALAR: 7
