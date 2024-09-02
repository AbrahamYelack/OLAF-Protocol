# Advanced Secure Protocol Design
## Quick Links
[Main Assignment Page](https://myuni.adelaide.edu.au/courses/95573/assignments/397468)  
[Submission of Implementation Page](https://myuni.adelaide.edu.au/courses/95573/assignments/397475)  
[Peer Review Feedback Page](https://myuni.adelaide.edu.au/courses/95573/assignments/397470)  
[OLAF Protocol GitHub Repository](https://github.com/xvk-64/2024-secure-programming-protocol)  

## Major Due Dates
2nd October - Submission of Implementation. This is a hard deadline and our marks get capped if we miss it.  
11th October - Peer Review Feedback. Another hard deadline which will have our marks capped if we miss it. This is just a constructive review on  think 3 other groups.  
18th October - Reflective Commentary.  

## More General Timeline
Week 2: Complete the initial design of the chat system's communication protocol.  
Week 4: Collaborative standardisation of the protocol with class-wide consensus.  
Week 6: Finalise detailed plans for code design and start your implementation.  
Week 8: Present a functional prototype in the tutorial for initial testing and feedback.  Consider this as the deadline to finish your implementation.  
Week 9: Submit the final version of the chat system for peer review. HARD DEADLINE: Wed, 02 Oct 2024. Late submission policy applies!  
Week 10: Conduct code reviews of three other groups' projects using both manual and automated code review techniques. Provide constructive feedback on the vulnerabilities found in peer reviews. DEADLINE for peer feedback: Friday, 11 Oct 2024. Late submission policy applies!  
Week 11: Submit a reflective commentary discussing the protocol standards, implementation challenges, thoughts on the embedded backdoors, and their detection difficulty.  Include in your submission the backdoor free, and your backdoored code.  DEADLINE: 18 Oct 2024. Late submission policy applies!  
Week 12: Participate in a friendly, ethical hackathon to test all chat systems for vulnerabilities and demonstrate proof of concept attacks in a VM environment.  

## Project Structure
`client.py`: Client side logic for connecting to the server and sending/recieving messages  
`server.py`: Server side logic for managing connections, messages and network state  
`crypto_utils.py`: Utility functions for handling encryption and key management  
`message.py`: Functions for constructing and validating messages  
`OLAF_Reference.md`: Reference documentation for the protocol everyone is going to use  

## Groupwork
Try to work in your own branches and use pull requests so we can manage everything nicely, and keep up nice documentation so its as straightforward as possible for us to all work on.

## OLAF Protocol Reference
The project is based on the OLAF/Neighbourhood protocol made by those sweats.  
Review the protocol documentation on their OLAF GitHub repository from the link above.


