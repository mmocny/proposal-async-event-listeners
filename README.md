# proposal-async-event-listeners

- Related proposal: https://github.com/whatwg/dom/issues/1308
- [TPAC 2024 Breakout session](https://www.w3.org/events/meetings/df616a60-8591-4f24-b305-aa0870aac1cb/)
- [Examples](./examples/)

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

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1a-non-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1a-non-passive-listeners.html)

It's entirely possible that developers wish to know about/respond to some events at a much lower priority than other competing tasks at around the same time. Currently there is no way to signal to the platform, that an event listener should be invoked asynchronously after the platform would ordinarily do so, saving the event listener's invocation for a less-busy/contentious time, in terms of task scheduling and execution.

`addEventListener(type, callback, { passive: true })` already exists, but currently only supported for various `touch`/`scroll` events.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1b-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1b-passive-listeners.html)
- [See polyfilled example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1c-polyfill-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1c-polyfill-passive-listeners.html)
- [See alternative polyfilled example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1d-better-polyfill-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1d-better-polyfill-passive-listeners.html)

One [improvement suggested beyond this is to add support for `{ priority }`](https://github.com/whatwg/dom/issues/1308), which implies "passive" or "async" but gives more control about the relative importance of this listner.

Passive observation is the default for features like Intersection Observer or some animation lifetime events.  Beyond adding support for passive for all UIEvents, there might other examples of non-passive events / callbacks / observers across the platform.

Properties:
- "passive" events do not expect support for `preventDefault`.
- Easy to polyfill or workaround, but, that makes it less accessible and less used.
- Polyfill might leave scheduling/performance opportunities on the table, especially if all registered event listeners are passive.
- Interop risks? it seems the fallback is just to existing behaviour...
- As a native feature, might be applied as a policy / intervention.
  - For example, constraining a third party script to only be allowed to register passive listeners.


## 2. Trouble flushing yieldy tasks before "document unload".

Today, because you can you can attach blocking event listeners (e.g. before every link click), you can easily **block the start of a navigation**, and prevent the unloading of the current document, by preventing the loading of a new document.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/2a-block-link-click.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/2a-block-link-click.html)

Note: The network request does not even begin until after the event is done processing (because of preventDefault / or potential to register late `beforeUnload`).


A well behaved script might choose to `passive`ly observe these events instead, allowing the UA to run the default actions, but, once a document starts unloading there is a limited amount of time for script to run.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/2b-unblock-link-click.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/2b-unblock-link-click.html)

As a result, many scripts hook onto events and delay the default action (such as a link navigaton or form submit) from even starting, for fear of not having enough time to observe the event otherwise.

Perhaps we can provide some assurances:
- If you were already in the position to block unload of the page, then
- Yielding (or passively observing) instead should not substantially change your ability to get scheduled before unload.


Scott Haseley has recently presented proposed features for `scheduler.postTask` which might be useful here.  `postTask` and `yield` already [support "inheritance"](https://docs.google.com/document/d/1rIOBBbkLh3w79hBrJ2IrZWmo5tzkVFc0spJHPE8iP-E/edit#heading=h.c484rp62uh2i).  Could we leverage this to add a flag that these tasks **already could have** blocked unload?

We might want to require an explicit signal `{ plzRunBeforeUnload: true }` so we don't prioritize tasks that ask for it.


## 3. Desire to track "async effects" which follow event dispatch.

Today it is hard to know when all the effects triggered by an event are complete.

For example, some sites might have many event listeners registered accross many components, and some observer tries to wait until "all work is complete", using very complex and careful coordination.

For any one discrete interaction there might be any number of unique event types that fire, each with capture/bubble phases, and then asynchronous api calls might follow.

Support for `passive` events would only add to this problem -- as now, even if you could observe and coordinate everything, you wouldn't quite know when to stop observing.

Some developers have asked for insights into the state of dispatch to event listeners (i.e. perhaps a count of registered + remaining).  Perhaps a single completion event would suffice. (Could that itself become a recursive problem?)

There are proposals to help with effects that span across asynchonous scheduling, such as the `AsyncContext` proposal.

Further: some developers have asked to be able to delay default action, and support for `preventDefault`, across async boundaries.  This seems difficult.

- For example: form validation which needs a network hop first.
- For example: modal dialog which requires a network hop before allowing dismissal.
- For example: How long after clicking on a button does the UI update?
  - Event Timing (and the metric INP) measure the initial latency: the very next paint, but,
  - Nothing measures performance of async hop into future animation frames (as is common with `await fetch()`)


## 4. Document loading: page has painted, but isn’t ready to receive input yet.

- Related to lazy-loading controllers but less fine grained. We have blocking=rendering for first paint but we don't have a way to block all events on resources like script.
- Very early interactions are racy, and the priority of event dispatch is unpredictably prioritized over async/defer scripts.


## 5. Lazy listeners and progressive hydration: Target isn’t ready to receive input, yet.

- You don't have the code to attach to addEventListener loaded yet, but the UI is already presented and the user could already interact.
- You want to delay any events from starting to dispatch, perhaps until some fetch / script finishes loading, or alternatively you just want a better mechanism to capture and replay the event later.
- Note: once the event listener is loaded, it becomes a normal synchronous event listener.
- Note: the declarative UI might have a declarative fallback (e.g. link click or form submit) but the imperative event might be "better" if allowed to load. Perhaps a timeout decides when to dispatch the default action?
