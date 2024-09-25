# proposal-async-event-listeners

- Related to: [proposal in whatwg/dom/issues/1308](https://github.com/whatwg/dom/issues/1308)
- [TPAC 2024 Breakout session](https://www.w3.org/events/meetings/df616a60-8591-4f24-b305-aa0870aac1cb/)
  - IRC channel: [https://irc.w3.org/?channels=%23async-event-listeners](https://irc.w3.org/?channels=%23async-event-listeners)
- [Examples](./examples/)

## Introduction

Building web applications requires dealing with inherantly asynchronous operations, but Event dispatch and Event Listeners are still inherantly synchronous.  Scheduling for event dispatch is even trickier.

This causes developers to reach for complex solutions, many of which are re-invented and repeated.  Let's discuss some of these issues:

1. Lack of support for `passive` Event Listeners.
2. Risks of deferring work due to "document unload".
3. Desire to track "async effects" which follow event dispatch.
4. Document loading: page has painted, but isn’t ready to receive input yet.
5. Lazy listeners and progressive hydration: Target isn’t ready to receive input, yet.


## 1. Lack of support for `passive` Event Listeners.

When some action happens on the web platform that results in firing events, **all event listeners** for that event are **immediately dispatched**.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1a-non-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1a-non-passive-listeners.html)

Developers often wish to respond to some events at a much lower priority, without blocking other work such as next paint.  Currently, there is no way to signal this to the platform.

Web performance advocates have been trying to teach [patterns like `await afterNextPaint()`](https://web.dev/articles/optimize-inp#yield_to_allow_rendering_work_to_occur_sooner):

- Synchronously, do work inherantly required to implement the default action.
- Schedule follow-on work that can be deferred.
- Yield.

But, many event listeners do not have **any** work needed to implement the default action.


#### Idea: `{ passive: true }`

`addEventListener` already supports the option for [`{ passive: true }`](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#passive), but currently only a few events related to scrolling actually dispatch passively.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1b-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1b-passive-listeners.html)
- [See polyfilled example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1c-polyfill-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1c-polyfill-passive-listeners.html)
- [See alternative polyfilled example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1d-better-polyfill-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1d-better-polyfill-passive-listeners.html)

Note: "passive" events **do not* expect support for `preventDefault`.

Note: this is easy to polyfill or workaround, but, that makes it less accessible and actually less used in practice.  Native support might have performance opportunities, especially if all registered event listeners are passive.  As a native feature, it might also be possible for the browser to implement restrictions or interventions: e.g. perhaps a specific `<script>` could be contrained to only support passive listeners.

#### Idea: `{ priority: 'background' }`

One [improvement suggested beyond this is to add support for `{ priority }`](https://github.com/whatwg/dom/issues/1308), which implies "passive" or "async" but gives more control about the relative importance of this listner.

#### Other details

- Passive observation is the default for some events already:
  - such as [Popover API events `beforetoggle` vs `toggle`](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API#events).
  - certain animation lifetime events
  - possible many others...
- Beyond UIEvents?  Other APIs with events / callbacks?
  - IntersectionObserver / PerformanceObserver designed to be inherantly async


## 2. Risks of deferring work due to "document unload".

Today, because you can you can attach blocking event listeners (e.g. before every link click), you can easily **block the start of a navigation**, and prevent the unloading of the current document.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/2a-block-link-click.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/2a-block-link-click.html)

Note: The network request does not even begin until after the event is done processing (because of preventDefault / or potential to register late `beforeUnload`).

A nice script might choose to `yield` or `passive`-ly observe these events instead.  But now, once a document starts unloading there is a very limited amount of time for tasks to get scheduled and execute.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/2b-unblock-link-click.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/2b-unblock-link-click.html)

As a result, many scripts hook onto events and delay the default action (such as a link navigaton or form submit) from even starting, for fear of not having enough time to observe the event otherwise.

#### Idea: add "assurances" for flushing before unload

- If a task could block unload of the page, then
- Yielding -- or passively observing events -- should be "flagged" as supporing flushing before unload, and
- Without blocking new document navigation start, or the current document unload.

Background: [`idleUntilUrgent()` pattern](https://philipwalton.com/articles/idle-until-urgent/) polyfills this idea using document lifecycle events.

Scott Haseley has recently presented proposed features for `scheduler.postTask` to address the broader use case.  Scheduler `postTask` and `yield` already [support "inheritance"](https://docs.google.com/document/d/1rIOBBbkLh3w79hBrJ2IrZWmo5tzkVFc0spJHPE8iP-E/edit#heading=h.c484rp62uh2i).

- Could we inherit another flag that these tasks **could have blocked unload**?
- Would we want an explicit signal `{ plzRunBeforeUnload: true }`?


## 3. Desire to track "async effects" which follow event dispatch.

Today it is hard to know when all the effects triggered by an interaction are complete.

Some sites create mechanisms to observe when "all work is complete", often requiring very complex instrumentation and careful coordination (wrapping browser apis, creating "zones", requiring build tooling, etc).

Support for `passive` events would only add to this problem, because instead of "one action, many effects" you almsot have "many actions".

#### Idea: track completion of all effects

Some developers have asked for insights into the state of dispatch to event listeners (have all listeners run to completion?).

There is also active work to track scheduled tasks back to an initiating Interaction.  i.e. Task attribution and the `AsyncContext` proposal.  Perhaps you might be able to observe tasks remaining (i.e. in TaskController) or when the last task has finished running (i.e. [FinalizationRegistry](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/FinalizationRegistry)).

#### Stretch goal: async support for preventDefault

Some developers have asked to be able to delay default action, and extend support for `preventDefault`, across async boundaries.  This seems difficult.

#### Use cases

- Some libraries will "debounce" **all events, always**.
  - The "real" listener is wrapped and delayed, even if just one animation frame.
  - The "real" listener might still be a single synchronous task.
- Form validation: which needs a network hop to decide.
- Modal dialog: several components might need to coordinate before allowing dismissal.
- Performance: How long after clicking on a button does the UI actually update?
  - Event Timing (and the metric INP) only measures the initial latency of the very next paint
  - Super common for events to `await fetch()` before updating page.


## 4. Document loading: page has painted, but isn’t ready to receive input yet.

We have `blocking=rendering` for first paint, but we don't have a way to `blocking=interactions`.

It is very recommended that sites server render the content of a page and allow client to start painting content, without depending on script.  Therefore, commonly early renderings are for pages without registered event listeners.

Waiting until after `DOMContentLoaded` fires is common.  Registering listeners from `<script defer>` or `<script type=module>` is implicitly running after `DOMContentLoaded`.

Many developers have reported that interactions very early with the page can appear to perform better than interactions that come later (counterintuitive)-- and found that this is because the interaction is worse than slow: it does nothing, and appears broken to the user.

Some workarounds have been:
- inlining javascript in the html
- semantic attributes on nodes, together with event capture + replay
  -  `on:click="..."`, `jsaction="click:..."`, `onClick$="..."`
- clever (ab)use of `<Form>`
  - It's great that actions work "without JavaScript", but
  - The fallback is to sumit a form and reload the page.  Slow.
  - Silly to do this especially if the script is already fetched and just waiting to execute.

#### Idea: Delay event dispatch, perhaps by decreasing task priority

Execution of script that registers event listeners, and the dispatch of events is already very racy.  Events already take time to arrive in browser, renderer process, etc, so there is already an existing lack of ordering guarentees.

Today, we don't know how long to wait before dispatching events, or which tasks to prioritize above event dispatch.

Today, we just don't wait for the page to settle at all.

Question: What about HitTesting and LayoutShifts?  Should we capture the target immediately?


## 5. Lazy listeners and progressive hydration: Target isn’t ready to receive input, yet.

Similar to (4), but expended through the full lifetime of the page and on a per-component level.

A common mantra we hear often is: web developers are **shipping too much JavaScript** and slowing down the page.  A mostly static component of the page, which offers some interaction functionality, but users rarely interact with it, should not need to be "initialized" until the user chooses to use it.

But the current design of event listevers motivates preloading and preregistering the full implementation for every possible feature on the page, or, building complex machinery for **event capture & replay**.


#### Idea: Capture events and replay when ready

The following is already a common pattern and is incredibly powerful:
- create tiny bundles of functionality for your page
  - Perhaps on component/ui boundaries or even for every specific event listener
- server render the page, without any requirement for script to run on client to render
- start to preload important bundle(s) with low-ish priority, based on predicted usage behaviour
  - Similar to speculation rules?
- when the user does interact switch to prioritized loading
  - similar to `idleUntilUrgent` pattern?
- Then, dispatch (or replay) the event.


This is complex, but generally great for users.  However, now the UA does not have insights into the "real" event listener.  Several web platform features break:

- `preventDefault` can get called pre-emptively
- [Transient User Activation](https://developer.mozilla.org/en-US/docs/Glossary/Transient_activation)
- Event Timing measurement of responsiveness
- Accessibility features
- ...anything else?


Perhaps native event listeners should be able to support this use case.

Strawman:
- Allow `addEventListeners` to support promises
  - `event.waitUntil` (service worker extendable events)
  - `event.intercept({ async handler() {} })` (navigation api)
  - `return promise` (ViewTransitions)
- Allow browser to lazy load listeners:
  - `loading=lazy` +
  - `blocking=interactions` per element +
  - `onclick="URL"`