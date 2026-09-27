## Inspiration

Healthcare professionals are constantly surrounded by physical pharmaceuticals, but the drugs themselves don't stay constant. In just the last five years, the FDA has approved over 230 new drugs and that pace makes it functionally impossible for any HCP to stay current on everything they've learned before and currently passing through their hands. In a 2025 editorial, the New England Journal of Medicine described clinicians as facing an ever-growing "haystack" of medical information, with their limited time making it increasingly difficult to find the information that actually matters.

Currently, these HCP's have a limited number of options when it comes to getting the information they need. They can physically search through medical literature themselves, ask pharmaceuticals to wait potentially a few days, or sign up for an automated text message system that could be missed by accident. We wanted to create a new way to engage HCPs beyond these options, so we eliminated the need for physicians to search, wait, or notice a message at all. Instead, we made the information something they could simply look at.

## What it does

Lens turns a physical drug sample into an interactive, spatial, clinical information tool using augmented reality. A clinician opens the iOS app, optionally selects the patient they're seeing, and points their phone at a drug sample. Lens automatically identifies the medication and overlays a personalized information bubble directly onto it, which stays anchored to the sample even as the clinician moves the phone. Depending on the HCP's speciality and history with the drug, the app will automatically decide which information is currently relevant and display accordingly. If a patient is selected, Lens checks that drug against the patient's recorded allergies, flagging anything worth a second look directly on the heads up display.

Once the initial scan is completed, the HCP can then ask a question out loud and Lens will retrieve the relevant information from a knowledge base of drug dossiers, generate a grounded answer, and read it back to you, creating a full conversation that allows the HCP to fully understand what they are working with. Afterwards, every scan and every question gets logged enabling the same HCP to view a web view of that history if they forgot anything or want to dive deeper.

## How we built it

Lens's drug detection pipeline runs entirely on-device. We trained a custom Create ML object detector on 1,000 images that achieves 92% accuracy in spatially locating medication bottles in real time. Once a bottle is detected, Lens combines OCR with barcode decoding to identify the specific drug without sending the camera feed to a server.

Behind the iOS experience, we built a FastAPI backend backed by MongoDB to manage personalized HCP and patient profiles, interaction history, and conversation data. To answer drug-specific questions and HCP follow-ups, we built a RAG pipeline of over 1,800+ openFDA documents. We embedded the documents using Sentence Transformers and kept them in an in-memory index, retrieving the most relevant context through cosine-similarity search. That retrieved context is then passed to xAI's Grok for generation through a custom system prompt that adapts response length to the HCP's familiarity tier and strictly constrains the model to information found in the retrieved sources. This is especially important because Lens speaks its responses aloud, so unsupported information cannot simply be dismissed as a bad chatbot response.

Finally, we built a React web dashboard that connects to the same backend, giving HCPs a persistent view of their interaction history and allowing them to revisit previous conversations and ask follow-up questions.

## Challenges we ran into

One of the hardest problems we faced was making personalization visible without slowing down the live AR experience. Lens has to perform detection, identify the drug, retrieve personalized information, check patient context, and update the AR interface quickly enough that it still feels like pointing a camera at an object rather than waiting on a search result. We solved this by keeping the vision pipeline on-device and separating the latency-sensitive detection and tracking from the backend calls needed for personalization and retrieval.

## Accomplishments that we're proud of

We are proud of bringing together systems that are typically separate, including computer vision, augmented reality, RAG, xAI, and voice interaction, into one coherent and easy-to-use workflow. Being able to build, customize, and ensure that these independently complex systems stayed in sync and could communicate quickly in real time is a huge accomplishment.

## What we learned

We learned how to build a hybrid RAG retrieval and ranking system without relying on a hosted vector database, while also developing a full-fledged FastAPI service to connect our iOS and React platforms. Getting all of these systems to work together quickly and reliably was one of our biggest challenges, but debugging these issues gave us valuable insight into how RAG pipelines, retrieval systems, APIs, and cross-platform architectures work together in practice.

## What's next for Lens

In the future, we'd move towards integrating Lens into smart glasses such as Meta Glasses to make the augmented reality interaction as seamless as possible. We'd also want to expand our drug database to cover the totality of the FDA and move our vector database to the cloud using services like MongoDB or AWS. Finally, we'd move clinician verification to something NPI-backed instead of self-registered and connect patient context to real EHRs.
