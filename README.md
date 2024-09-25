# proposal-async-event-listeners

- Related [proposal in whatwg/dom/issues/1308](https://github.com/whatwg/dom/issues/1308)
- [TPAC 2024 Breakout session](https://www.w3.org/events/meetings/df616a60-8591-4f24-b305-aa0870aac1cb/)
- [Examples](./examples/)

## Introduction

Building web applications requires dealing with inherantly asynchronous operations, and increasingly so.  But Event dispatch and Event Listeners is still inherantly synchronous. 
 Scheduling of event dispatch is even trickier.

This causes a range of issues which can require complex solutions, many of which are re-invented and repeated.

Let's discuss some of these issues:

1. Lack of support for `passive` Event Listeners.
2. Trouble flushing post-processing work before "document unload".
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


#### `{ passive: true }`

[]`addEventListener` already supports the option for `{ passive: true }`](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#passive), but currently only a few events related to scrolling actually dispatch passively.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1b-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1b-passive-listeners.html)
- [See polyfilled example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1c-polyfill-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1c-polyfill-passive-listeners.html)
- [See alternative polyfilled example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/1d-better-polyfill-passive-listeners.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/1d-better-polyfill-passive-listeners.html)

Note: "passive" events **do not* expect support for `preventDefault`.

Note: this is easy to polyfill or workaround, but, that makes it less accessible and actually less used in practice.  Native support might have performance opportunities, especially if all registered event listeners are passive.  As a native feature, it might also be possible for the browser to implement restrictions or interventions: e.g. perhaps a specific `<script>` could be contrained to only support passive listeners.

#### `{ priority: 'background' }`

One [improvement suggested beyond this is to add support for `{ priority }`](https://github.com/whatwg/dom/issues/1308), which implies "passive" or "async" but gives more control about the relative importance of this listner.

#### Other details

Passive observation is the default for some events already (such as [Popover API Events' `beforetoggle` vs `toggle`](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API#events)).  Features like Intersection Observer or some animation lifetime events.  Beyond adding support for passive for all UIEvents, there might other examples of non-passive events / callbacks / observers across the platform.


## 2. Trouble flushing yieldy tasks before "document unload".

Today, because you can you can attach blocking event listeners (e.g. before every link click), you can easily **block the start of a navigation**, and prevent the unloading of the current document, by preventing the loading of a new document.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/2a-block-link-click.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/2a-block-link-click.html)

Note: The network request does not even begin until after the event is done processing (because of preventDefault / or potential to register late `beforeUnload`).


A well behaved script might choose to `passive`ly observe these events instead, allowing the UA to run the default actions, but, once a document starts unloading there is a limited amount of time for script to run.

- [See example](https://github.com/mmocny/proposal-async-event-listeners/blob/main/examples/2b-unblock-link-click.html) or [Try it](https://mmocny.com/proposal-async-event-listeners/examples/2b-unblock-link-click.html)

As a result, many scripts hook onto events and delay the default action (such as a link navigaton or form submit) from even starting, for fear of not having enough time to observe the event otherwise.

Perhaps we can provide some assurances:
- If a task could block unload of the page, then
- Yielding -- or passively observing events -- should not substantially decrease the odds of being scheduled.
- Should not need to block the new document from loading in.
- We already allow the event loop to run for some time after navigation to next document.
  - We just don't prioritize, or factor in any signals.
  - There are differences between same origin and cross origin navigation...
- Background: [`idleUntilUrgent()` pattern](https://philipwalton.com/articles/idle-until-urgent/)


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

For example:
- Some libraries will "debounce" ALL events, always.  The "real" listener is wrapped and delayed.
- form validation which needs a network hop first.
- modal dialog which requires a network hop before allowing dismissal.
- How long after clicking on a button does the UI update?
  - Event Timing (and the metric INP) measure the initial latency: the very next paint, but,
  - Nothing measures performance of async hop into future animation frames (as is common with `await fetch()`)


## 4. Document loading: page has painted, but isn’t ready to receive input yet.

We have `blocking=rendering` for first paint, but we don't have a way to `blocking=interactions`.

It is very common for sites to render the content of the page before executing any script that registers necessary event listeners.  Registering event listeners after `DOMContentLoaded` fires is common.  Registering listeners from `<script defer>` or `<script type=module>` is implicitly running after `DOMContentLoaded`.

On more sophisticated sites, especailly those that use frameworks which might require lots of bootstrapping, the gap can be so large that some developers have invented special mechanisms to capture very early interactions:

- inlining javascript in the html
- semantic attributes on nodes, together with event capture + replay
  -  `on:click="..."`, `jsaction="click:..."`, `onClick$="..."`
- clever (ab)use of `<Form>`
  - It's great that actions work "without JavaScript" but the fallback experience can be worse
  - and, silly to fallback when the script is already fetched and just waiting to run... might be much slower submit form.

Many developers observe that interactions very early with the page, even while it is busy loading, can appear to perform better than interactions that come later-- because the interaction might still do nothing at all and appear broken to the user.

Worse: the registration of event listeners and dispatch of events is very racy.  The priority of event dispatch is higher than script execution -- even if the script is loaded and ready to run.

When the even loop is full of tasks that need running, we don't know how long to wait before dispatching events.  Today we don't wait at all.


## 5. Lazy listeners and progressive hydration: Target isn’t ready to receive input, yet.

Similar to (4) but expended through the full lifetime of the page.

A common mantra we hear often is: web developers are **shipping too much JavaScript** and slowing down the page.

But the current design of event listevers really motivates preloading and preregistering the full implementation for every possible feature on the page, or, building complex machinery for **event capture + replay**, often with synthetic event dispatch at the framework level.

An increasingly common pattern is actually incredibly powerful:
- create tiny bundles of functionality for specific components (or even specific events)
- server render the initial, often static UI, and lazily preload the bundle
- when the user interacts, capture the event, and switch to prioritized loading of the bundle
  - similar to `idleUntilUrgent` pattern.
  - might even try to predict an interaction will come soon, (like speculation rules)
- then, replay the event.


This is complex, but generally great for users.  However, the UA does not have insights into this and several web platform features break:

- `preventDefault` can get called pre-emptively
- [Transient User Activation](https://developer.mozilla.org/en-US/docs/Glossary/Transient_activation)
- Event Timing measurement of responsiveness
- etc..


Ideas:
- Allow `addEventListeners` to support promises
  - `event.waitUntil` (service worker extendable events)
  - `event.intercept({ async handler() {} })` (navigation api)
  - `return promise` (ViewTransitions)
- After HitTest, but before event dispatch, confirm that events are registered.
  - Strawman: `addEventListenerInitializer`
- Let browser co-ordinate loading:
  - onclick
  - `onclick="URL"`

