# proposal-async-event-listeners

- Related proposal: https://github.com/whatwg/dom/issues/1308
- [TPAC 2024 Breakout session](https://www.w3.org/events/meetings/df616a60-8591-4f24-b305-aa0870aac1cb/)

## Introduction

Building web applications requires dealing with inherantly asynchronous operations, and increasingly so.  As web developers, we have a lot of great tools for this -- but Event Listeners are still inherantly synchronous -- and the task scheduling policies for event dispatch is particularly tricky.  This causes a range of issues which can require complex solutions, many of which are re-invented or repeated.

Let's discuss some of these issues:

1. Lack of support for `passive` Event Listeners.
2. Trouble flushing post-processing work before "document unload".
3. Desire to track "async effects" which follow event dispatch.
4. Document loading: page has painted, but isn’t ready to receive input yet.
5. Lazy listeners and progressive hydration: Target isn’t ready to receive input, yet.


## 1. Lack of support for `passive` Event Listeners.

When some action happens on the web platform that results in firing events, **all event listeners** for that event are **immediately dispatched**, right then & there on the spot, without regard to the priority of the listener relative to surrounding tasks.

It's entirely possible that developers wish to know about/respond to some events at a much lower priority than other competing tasks at around the same time. Currently there is no way to signal to the platform, that an event listener should be invoked asynchronously after the platform would ordinarily do so, saving the event listener's invocation for a less-busy/contentious time, in terms of task scheduling and execution.

- This event listener needs to observe the event, but doesn't actually implement the core functionality of the event and doesn't need to be scheduled immediately and before next paint.
- Already supported for various scroll events, and for specific features like Intersection Observer and some animation lifetime events, etc.
- Easy to polyfill or workaround, as an opt-in, but might leave scheduling/performance opportunities on the table.
- As a native feature, might be applied as a policy / intervention. For example, constraining a third party script to only be allowed to register passive listeners.
- Note: {priority} seems to me to imply "passive" yet gives even more control.

## 2. Trouble flushing yieldy tasks before "document unload".

- Today you can easily block the start of a navigation that would unload a document, but, once a document starts unloading there is a limited amount of time for script.
- As a result, many scripts hook onto events and delay the default action (such as a link navigaton or form submit) from even starting, for fear of not having a change to observe the event at all when that event triggers document unload.
- Perhaps we need a contract: This event listener is only passively attached to this event... but it should be "flushed" before unload. (Reminder: these scripts are already blocking unload start, anyway)

## 3. Desire to track "async effects" which follow event dispatch.

- AsyncContext proposal would help track the context... but when is the effect complete?
- Might still want to be able to preventDefault etc from the async.
  - e.g. form validation which needs a network hop first.
  - e.g. modal dialog which requires a network hop before allowing dismissal.
- Might want other web platform features, like performance event timing, to measure all the way to the end of async effects.

## 4. Document loading: page has painted, but isn’t ready to receive input yet.

- Related to lazy-loading controllers but less fine grained. We have blocking=rendering for first paint but we don't have a way to block all events on resources like script.
- Very early interactions are racy, and the priority of event dispatch is unpredictably prioritized over async/defer scripts.

## 5. Lazy listeners and progressive hydration: Target isn’t ready to receive input, yet.

- You don't have the code to attach to addEventListener loaded yet, but the UI is already presented and the user could already interact.
- You want to delay any events from starting to dispatch, perhaps until some fetch / script finishes loading, or alternatively you just want a better mechanism to capture and replay the event later.
- Note: once the event listener is loaded, it becomes a normal synchronous event listener.
- Note: the declarative UI might have a declarative fallback (e.g. link click or form submit) but the imperative event might be "better" if allowed to load. Perhaps a timeout decides when to dispatch the default action?
