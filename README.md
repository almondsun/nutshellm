# nutsheLLM 

Let me introduce the project idea I propose for the Build with Paritok hackathon.

The project is called nutsheLLM.

The core problem we want to address is simple: modern AI agents often send enormous amounts of context to language models. This context may contain source code, logs, documentation, previous conversations, tool outputs and repeated information.

Most of that information is useful, but not all of it needs to be transmitted in its original form.

The result is higher API costs, longer response times and unnecessary token consumption.

nutsheLLM is an intelligent context-efficiency layer for AI applications and agents.

It sits between an AI application and the final language model. Before a request reaches the LLM, nutsheLLM analyzes the context, identifies which information is critical, and uses Paritok to compress the parts that can safely be reduced.

However, nutsheLLM is not intended to be just another compression proxy.

Its main differentiator is that it evaluates whether the compressed context still allows the model to complete the task correctly.

The central question of the project is not simply:

“How many tokens did we remove?”

It is:

“How many tokens can we remove while preserving useful task performance?”

The system classifies context into three categories.

First, immutable information, which should remain almost exactly as written. This includes error codes, numerical measurements, function names, API signatures, file paths and stack traces.

Second, compressible information, such as long explanations, repetitive logs, tool outputs and historical conversation context.

Third, disposable information, including duplicates, boilerplate and irrelevant details.

After this analysis, nutsheLLM creates two possible execution paths.

The baseline path sends the original context directly to the LLM.

The optimized path sends a Paritok-compressed version of the same context.

The system then compares the results using metrics such as token reduction, cost, latency, factual preservation and task success.

For tasks involving code, we can check whether the suggested patch compiles or passes tests.

For debugging tasks, we can verify whether the model identifies the correct root cause.

For incident-response tasks, we can check whether critical facts, timestamps and error messages were preserved.

If the compressed request fails its validation checks, nutsheLLM can automatically retry using a less aggressive compression level or the complete original context.

This introduces one of the project’s most important concepts:

nutsheLLM should not only know how to compress context. It should know when not to compress it.

# INSPIRATION

From an implementation perspective, we can draw inspiration from three open-source projects.

Headroom can guide the context-processing and observability architecture.

LiteLLM can inspire provider routing, usage tracking and gateway design.

LLMLingua can help us understand compression evaluation.

Nevertheless, Paritok must remain the central compression technology used by the hackathon submission.

# In one sentence:

nutsheLLM is an adaptive context-efficiency platform that helps AI agents use fewer tokens, reduce costs and maintain task quality by compressing only what is safe to compress.

The reason I believe this project could be competitive is that it demonstrates Paritok through a real, measurable workflow rather than simply adding it to a chatbot.

The judges would be able to see exactly what information was compressed, what was preserved, how much was saved and whether the AI still completed the task successfully.

Our objective would not be to claim that less context is always better.

Our objective would be to prove that AI systems can use context more intelligently.
